# -*- coding: utf-8 -*-
from django.test import TestCase
from AssetStorm.assets.models import AssetType
import json


class TestAssetFixtureValidity(TestCase):
    fixtures = [
        'span_assets.yaml',
        'caption-span_assets.yaml',
        'block_assets.yaml',
        'table.yaml',
        'article_assets'
    ]

    def test_schemas_are_json(self):
        for at in AssetType.objects.all():
            if at.schema is None:
                continue
            self.assertIs(type(at.schema), dict, msg="The schema of {} ({}) is not JSON: {}".format(
                at.type_name, at.pk, at.schema))
            self.assertEqual(json.loads(json.dumps(at.schema)), at.schema)
