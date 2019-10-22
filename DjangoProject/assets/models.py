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
    invalidation_list = ArrayField(models.IntegerField(), blank=True, null=True)

    @staticmethod
    def get_asset_content(content_type, content_id):
        if content_type == 1:  # text
            return Text.objects.get(pk=content_id).text
        elif content_type == 2:  # uri-element
            return UriElement.objects.get(pk=content_id).uri
        elif content_type == 3:  # enum
            return Enum.objects.get(pk=content_id).item
        else:
            return Asset.objects.get(pk=uuid.UUID(content_id)).content

    @property
    def content(self):
        if self.content_cache is not None:
            return self.content_cache
        content = {
            'type': self.t.type_name,
            'id': str(self.pk)
        }
        for k in self.content_ids.keys():
            if type(self.t.schema[k]) is list:
                asset_content = [self.get_asset_content(self.t.schema[k][0], e) for e in self.content_ids[k]]
            elif type(self.t.schema[k]) is dict and \
                    len(self.t.schema[k].keys()) == 1 and \
                    "3" in self.t.schema[k].keys():
                asset_content = self.get_asset_content(3, self.content_ids[k])
            else:
                asset_content = self.get_asset_content(self.t.schema[k], self.content_ids[k])
            content[k] = asset_content
        return content


class Text(models.Model):
    text = models.TextField()


class UriElement(models.Model):
    uri = models.CharField(max_length=256)


class Enum(models.Model):
    t = models.ForeignKey(EnumType, on_delete=models.CASCADE)
    item = models.TextField()
