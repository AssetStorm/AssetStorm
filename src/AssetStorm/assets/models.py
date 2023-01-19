# -*- coding: utf-8 -*-
from django.db import models
from django.db.models.fields.json import JSONField
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from copy import deepcopy
import uuid
import re


class AssetType(models.Model):
    type_name = models.CharField(unique=True, max_length=128)
    parent_type = models.ForeignKey('self', related_name="children", on_delete=models.SET_NULL, blank=True, null=True)
    schema = JSONField(blank=True, null=True)
    templates = JSONField(default=dict)

    def __str__(self):
        schema_str = "?" if self.schema is None else "!"
        return "<AssetType %d: %s %s>" % (self.pk, self.type_name, schema_str)


class EnumType(models.Model):
    items = ArrayField(models.TextField())


class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    t = models.ForeignKey(AssetType, on_delete=models.CASCADE, related_name="assets")
    content_cache = JSONField(blank=True, null=True)
    text_reference_list = ArrayField(models.IntegerField(), default=list)
    uri_reference_list = ArrayField(models.IntegerField(), default=list)
    enum_reference_list = ArrayField(models.IntegerField(), default=list)
    asset_reference_list = ArrayField(
        models.UUIDField(default=uuid.uuid4, editable=False, blank=False, null=False), default=list)
    revision_chain = models.ForeignKey("self", on_delete=models.SET_NULL,
                                       related_name="new_version", blank=True, null=True)
    raw_content_cache = models.TextField(null=True, default=None)

    def clear_reference_lists(self):
        self.text_reference_list.clear()
        self.uri_reference_list.clear()
        self.enum_reference_list.clear()
        self.asset_reference_list.clear()

    def register_reference_to_text(self, text):
        if text.pk not in self.text_reference_list:
            self.text_reference_list.append(text.pk)

    def register_reference_to_uri(self, uri):
        if uri.pk not in self.uri_reference_list:
            self.uri_reference_list.append(uri.pk)

    def register_reference_to_enum(self, enum):
        if enum.pk not in self.enum_reference_list:
            self.enum_reference_list.append(enum.pk)

    def register_reference_to_sub_asset(self, sub_asset):
        if sub_asset.pk not in self.asset_reference_list:
            self.asset_reference_list.append(sub_asset.pk)

    def get_asset_content(self, content_type, content_id):
        if content_type == 1:  # text
            text = Text.objects.get(pk=content_id)
            self.register_reference_to_text(text)
            return text.text
        elif content_type == 2:  # uri-element
            uri_element = UriElement.objects.get(pk=content_id)
            self.register_reference_to_uri(uri_element)
            return uri_element.uri
        elif type(content_type) is dict and "3" in content_type:  # enum
            enum = Enum.objects.get(pk=content_id)
            self.register_reference_to_enum(enum)
            return enum.item
        else:
            sub_asset = Asset.objects.get(pk=uuid.UUID(content_id))
            self.register_reference_to_sub_asset(sub_asset)
            return sub_asset.content

    @property
    def change_chain(self):
        if self.changes.count() > 0:
            return self.changes.order_by("time").last()
        else:
            return None

    @property
    def content(self):
        if self.content_cache is not None:
            return self.content_cache
        self.clear_reference_lists()
        self.content_cache = {
            'type': self.t.type_name,
            'id': str(self.pk)
        }
        for k in self.change_chain.structure.keys():
            if type(self.t.schema[k]) is list:
                asset_content = [
                    self.get_asset_content(self.t.schema[k][0], e)
                    for e in self.change_chain.structure[k]
                ]
            elif type(self.t.schema[k]) is dict and \
                    len(self.t.schema[k].keys()) == 1 and \
                    "3" in self.t.schema[k].keys():
                asset_content = self.get_asset_content(self.t.schema[k], self.change_chain.structure[k])
            else:
                asset_content = self.get_asset_content(self.t.schema[k], self.change_chain.structure[k])
            self.content_cache[k] = asset_content
        self.save()
        return self.content_cache

    def clear_cache(self):
        for asset in Asset.objects.filter(asset_reference_list__contains=[self.pk]):
            asset.clear_cache()
        self.content_cache = None
        self.raw_content_cache = None
        self.clear_reference_lists()
        self.save()

    @classmethod
    def produce(cls, t: AssetType, content_ids: dict):
        a = Asset(t=t)
        a.save()
        change_chain = None
        for key in t.schema:
            if key not in content_ids:
                raise StructureError("The key %s is missing in the content_ids." % key)
            change_chain = AssetChange(time=timezone.now(), asset=a, parent=change_chain,
                                       key=key, inserts=content_ids[key])
            change_chain = change_chain.bubble()
        return a

    def change(self, key: str, position: int = 0, delete_count: int = 0, inserts=None):
        if inserts is None:
            inserts = []
        new_change = AssetChange(asset=self, parent=self.change_chain, key=key,
                                 position=position, delete=delete_count, inserts=inserts)
        new_change.bubble()

    def render_template(self, template_key="raw"):
        def get_key_content(type_id, pk):
            if type_id == 1:
                return Text.objects.get(pk=pk).text
            if type_id == 2:
                return UriElement.objects.get(pk=pk).uri
            if type(type_id) is dict and "3" in type_id:
                return Enum.objects.get(pk=pk).item
            return Asset.objects.get(pk=pk).render_template(template_key=template_key)

        if template_key not in self.t.templates.keys():
            return ""
        if template_key == "raw":
            if self.raw_content_cache is not None:
                return self.raw_content_cache
        consumable_template = self.t.templates[template_key]
        for key in self.t.schema.keys():
            key_list_regex = r"^(?P<start_part>[\s\S]*?){{for\(" + key + \
                             r"\)}}(?P<list_template>[\s\S]*?){{endfor}}(?P<end_part>[\s\S]*)"
            key_regex = r"^(?P<start_part>[\s\S]*?){{" + key + r"}}(?P<end_part>[\s\S]*)"
            list_matches = re.match(key_list_regex, consumable_template, re.MULTILINE)
            while list_matches and type(self.t.schema[key]) is list:
                list_content = ""
                for pk in self.change_chain.structure[key]:
                    consumable_list_template = list_matches.groupdict()["list_template"]
                    matches = re.match(key_regex, consumable_list_template, re.MULTILINE)
                    while matches:
                        consumable_list_template = matches.groupdict()["start_part"] + get_key_content(
                            self.t.schema[key][0], pk) + matches.groupdict()["end_part"]
                        matches = re.match(key_regex, consumable_list_template, re.MULTILINE)
                    list_content += consumable_list_template
                consumable_template = str(list_matches.groupdict()["start_part"]) + \
                    list_content + \
                    str(list_matches.groupdict()["end_part"])
                list_matches = re.match(key_list_regex, consumable_template, re.MULTILINE)
            matches = re.match(key_regex, consumable_template, re.MULTILINE)
            while matches:
                consumable_template = matches.groupdict()["start_part"] + get_key_content(
                    self.t.schema[key], self.change_chain.structure[key]) + matches.groupdict()["end_part"]
                matches = re.match(key_regex, consumable_template, re.MULTILINE)
        if template_key == "raw":
            self.raw_content_cache = consumable_template
            self.save()
        return consumable_template


class AssetChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    time = models.DateTimeField(auto_now=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, null=True, default=None, related_name="changes")
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name="child", null=True, default=None)
    key = models.CharField(max_length=128)
    position = models.IntegerField(default=0)
    delete = models.IntegerField(default=0)
    inserts = JSONField(blank=True, null=True, default=None)
    structure_cache = JSONField(blank=True, null=True, default=None)

    def __str__(self):
        return "<AssetChange %s Key:%s (%d|%d|%s) -- %s>" % (self.pk, self.key,
                                                             self.position, self.delete, str(self.inserts),
                                                             str(self.parent))

    @property
    def structure(self):
        if self.structure_cache is not None:
            return self.structure_cache
        else:
            if self.parent is None:
                structure = deepcopy(self.asset.t.schema)
                for key in structure.keys():
                    if type(structure[key]) is list:
                        structure[key] = []
                    else:
                        structure[key] = None
            else:
                structure = self.parent.structure
            if type(structure[self.key]) is list:
                del structure[self.key][self.position:self.position+self.delete]
                for i, insertion in enumerate(self.inserts):
                    structure[self.key].insert(self.position + i, insertion)
            else:
                structure[self.key] = self.inserts
            self.structure_cache = structure
            self.save()
            return structure

    def invalidate_structure_cache(self):
        self.structure_cache = None
        self.save()
        for c in self.child:
            c.invalidate_structure_cache()

    def bubble(self):
        if self.parent is not None and self.parent.time > self.time:
            p = self.parent
            self.parent = p.parent
            p.parent = self
            p.invalidate_structure_cache()
            p.save()
            self.bubble()
            self.save()
            return p
        else:
            self.save()
            return self


class Text(models.Model):
    text = models.TextField()


class UriElement(models.Model):
    uri = models.TextField()


class Enum(models.Model):
    t = models.ForeignKey(EnumType, on_delete=models.CASCADE)
    item = models.TextField()


class StructureError(Exception):
    pass
