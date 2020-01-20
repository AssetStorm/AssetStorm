# -*- coding: utf-8 -*-
from django.test import TestCase
from django.core.management import call_command

from AssetStorm.assets.models import Text, Asset, AssetType


class TestBuildCaches(TestCase):
    fixtures = [
        'span_assets.yaml',
        'caption-span_assets.yaml',
        'block_assets.yaml',
        'table.yaml',
        'enum_types.yaml'
    ]

    def test_single_asset(self):
        t = Text(text="Foohoo!")
        t.save()
        asset = Asset(t=AssetType.objects.get(type_name="span-regular"), content_ids={"text": t.pk})
        asset.save()
        self.assertIsNone(asset.content_cache)
        self.assertIsNone(asset.raw_content_cache)
        call_command("build_caches")
        reloaded_asset = Asset.objects.get(pk=asset.pk)
        self.assertIsNotNone(reloaded_asset.content_cache)
        self.assertIsNotNone(reloaded_asset.raw_content_cache)
        self.assertEqual(reloaded_asset.content_cache, {
            "id": str(asset.pk),
            "type": "span-regular",
            "text": "Foohoo!"
        })
        self.assertEqual(reloaded_asset.raw_content_cache, "Foohoo!")

    def test_partially_existent_caches(self):
        t1 = Text(text="Text1")
        t1.save()
        t2 = Text(text="Text2")
        t2.save()
        a1 = Asset(t=AssetType.objects.get(type_name="span-regular"), content_ids={"text": t1.pk})
        a1.save()
        a2 = Asset(t=AssetType.objects.get(type_name="span-emphasized"), content_ids={"text": t2.pk})
        a2.save()
        self.assertIsNone(a1.content_cache)
        self.assertIsNone(a1.raw_content_cache)
        self.assertIsNone(a2.content_cache)
        self.assertIsNone(a2.raw_content_cache)
        self.assertEqual(a1.content, {
            "id": str(a1.pk),
            "type": "span-regular",
            "text": "Text1"
        })
        self.assertIsNotNone(a1.content_cache)
        self.assertIsNone(a1.raw_content_cache)
        self.assertEqual(a1.content_cache, {
            "id": str(a1.pk),
            "type": "span-regular",
            "text": "Text1"
        })
        self.assertEqual(a2.render_template(), "Text2")
        self.assertIsNone(a2.content_cache)
        self.assertIsNotNone(a2.raw_content_cache)
        self.assertEqual(a2.raw_content_cache, "Text2")
        call_command("build_caches")
        r_a1 = Asset.objects.get(pk=a1.pk)
        r_a2 = Asset.objects.get(pk=a2.pk)
        self.assertIsNotNone(r_a1.content_cache)
        self.assertIsNotNone(r_a1.raw_content_cache)
        self.assertIsNotNone(r_a2.content_cache)
        self.assertIsNotNone(r_a2.raw_content_cache)
        self.assertEqual(r_a1.content_cache, {
            "id": str(r_a1.pk),
            "type": "span-regular",
            "text": "Text1"
        })
        self.assertEqual(r_a1.raw_content_cache, "Text1")
        self.assertEqual(r_a2.content_cache, {
            "id": str(r_a2.pk),
            "type": "span-emphasized",
            "text": "Text2"
        })
        self.assertEqual(r_a2.raw_content_cache, "Text2")
