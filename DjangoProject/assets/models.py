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
    asset_reference_list = ArrayField(
        models.UUIDField(default=uuid.uuid4, editable=False, blank=False, null=False),
        blank=True, null=True)
    revision_chain = models.ForeignKey("self", on_delete=models.SET_NULL,
                                       related_name="new_version", blank=True, null=True)

    @staticmethod
    def get_asset_content(content_type, content_id, invalidation_list):
        if content_type == 1:  # text
            return Text.objects.get(pk=content_id).text
        elif content_type == 2:  # uri-element
            return UriElement.objects.get(pk=content_id).uri
        elif content_type == 3:  # enum
            return Enum.objects.get(pk=content_id).item
        else:
            return Asset.objects.get(pk=uuid.UUID(content_id)).get_content(invalidation_list=invalidation_list)

    def get_content(self, invalidation_list=[]):
        if self.invalidation_list is None:
            self.invalidation_list = []
        for uid in invalidation_list:
            self.invalidation_list.append(uid)
        invalidation_list.append(self.pk)
        if self.content_cache is not None:
            self.save()
            return self.content_cache
        self.content_cache = {
            'type': self.t.type_name,
            'id': str(self.pk)
        }
        for k in self.content_ids.keys():
            if type(self.t.schema[k]) is list:
                asset_content = [
                    self.get_asset_content(self.t.schema[k][0], e, invalidation_list=invalidation_list)
                    for e in self.content_ids[k]
                ]
            elif type(self.t.schema[k]) is dict and \
                    len(self.t.schema[k].keys()) == 1 and \
                    "3" in self.t.schema[k].keys():
                asset_content = self.get_asset_content(3, self.content_ids[k],
                                                       invalidation_list=invalidation_list)
            else:
                asset_content = self.get_asset_content(self.t.schema[k], self.content_ids[k],
                                                       invalidation_list=invalidation_list)
            self.content_cache[k] = asset_content
        self.save()
        return self.content_cache

    @property
    def content(self):
        return self.get_content(invalidation_list=[])

    def clear_cache(self):
        if self.invalidation_list is not None:
            for asset in Asset.objects.filter(pk__in=self.invalidation_list):
                asset.clear_cache()
        self.content_cache = None
        self.save()


class Text(models.Model):
    text = models.TextField()


class UriElement(models.Model):
    uri = models.CharField(max_length=256)


class Enum(models.Model):
    t = models.ForeignKey(EnumType, on_delete=models.CASCADE)
    item = models.TextField()
