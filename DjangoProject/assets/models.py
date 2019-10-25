# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.postgres.fields import JSONField, ArrayField
import uuid


class AssetType(models.Model):
    type_name = models.CharField(unique=True, max_length=128)
    parent_type = models.ForeignKey('self', related_name="children", on_delete=models.SET_NULL, blank=True, null=True)
    schema = JSONField(blank=True, null=True)

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
        elif content_type == 3:  # enum
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
                asset_content = self.get_asset_content(3, self.content_ids[k])
            else:
                asset_content = self.get_asset_content(self.t.schema[k], self.content_ids[k])
            self.content_cache[k] = asset_content
        self.save()
        return self.content_cache

    def clear_cache(self):
        for asset in Asset.objects.filter(asset_reference_list__contains=[self.pk]):
            asset.clear_cache()
        self.content_cache = None
        self.clear_reference_lists()
        self.save()


class Text(models.Model):
    text = models.TextField()


class UriElement(models.Model):
    uri = models.CharField(max_length=256)


class Enum(models.Model):
    t = models.ForeignKey(EnumType, on_delete=models.CASCADE)
    item = models.TextField()
