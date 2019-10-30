# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.postgres.fields import JSONField, ArrayField
import uuid
import re


class AssetType(models.Model):
    type_name = models.CharField(unique=True, max_length=128)
    parent_type = models.ForeignKey('self', related_name="children", on_delete=models.SET_NULL, blank=True, null=True)
    schema = JSONField(blank=True, null=True)
    templates = JSONField(default=dict)

    def __str__(self):
        schema_str = "?" if self.schema is None else "!"
        return "(" + str(self.pk) + ") " + self.type_name + " " + schema_str


class EnumType(models.Model):
    items = ArrayField(models.TextField())


class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    t = models.ForeignKey(AssetType, on_delete=models.CASCADE, related_name="assets")
    content_ids = JSONField(blank=True, null=True)
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
    def content(self):
        if self.content_cache is not None:
            return self.content_cache
        self.clear_reference_lists()
        self.content_cache = {
            'type': self.t.type_name,
            'id': str(self.pk)
        }
        for k in self.content_ids.keys():
            if type(self.t.schema[k]) is list:
                asset_content = [
                    self.get_asset_content(self.t.schema[k][0], e)
                    for e in self.content_ids[k]
                ]
            elif type(self.t.schema[k]) is dict and \
                    len(self.t.schema[k].keys()) == 1 and \
                    "3" in self.t.schema[k].keys():
                asset_content = self.get_asset_content(self.t.schema[k], self.content_ids[k])
            else:
                asset_content = self.get_asset_content(self.t.schema[k], self.content_ids[k])
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
                for pk in self.content_ids[key]:
                    consumable_list_template = list_matches.groupdict()["list_template"]
                    matches = re.match(key_regex, consumable_list_template, re.MULTILINE)
                    while matches:
                        consumable_list_template = matches.groupdict()["start_part"] + get_key_content(
                            self.t.schema[key][0], pk) + matches.groupdict()["end_part"]
                        matches = re.match(key_regex, consumable_list_template, re.MULTILINE)
                    list_content += consumable_list_template
                consumable_template = list_matches.groupdict()["start_part"] + \
                    list_content + \
                    list_matches.groupdict()["end_part"]
                list_matches = re.match(key_list_regex, consumable_template, re.MULTILINE)
            matches = re.match(key_regex, consumable_template, re.MULTILINE)
            while matches:
                consumable_template = matches.groupdict()["start_part"] + get_key_content(
                    self.t.schema[key], self.content_ids[key]) + matches.groupdict()["end_part"]
                matches = re.match(key_regex, consumable_template, re.MULTILINE)
        if template_key == "raw":
            self.raw_content_cache = consumable_template
            self.save()
        return consumable_template


class Text(models.Model):
    text = models.TextField()


class UriElement(models.Model):
    uri = models.CharField(max_length=256)


class Enum(models.Model):
    t = models.ForeignKey(EnumType, on_delete=models.CASCADE)
    item = models.TextField()
