# -*- coding: utf-8 -*-
from django.test import TestCase
from django.test import Client
from django.urls import reverse
from assets.models import AssetType
import json
import os


class TestSaveAsset(TestCase):
    fixtures = [
        'span_assets.yaml',
        'caption-span_assets.yaml',
        'block_assets.yaml',
        'table.yaml',
        'enums.yaml'
    ]

    def setUp(self) -> None:
        self.client = Client()
        article = AssetType(type_name="article", schema={
            "title": 1,
            "subtitle": 1,
            "author": 1,
            "abstract": 1,
            "content": [AssetType.objects.get(type_name="block").pk]
        })
        article.save()

    def test_no_JSON(self):
        response = self.client.post(reverse('save_asset'),
                                    data="Foo",
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "Error": "Request not in JSON format. The requests body has to be valid JSON."
        })

    def test_no_type(self):
        response = self.client.post(reverse('save_asset'),
                                    data={"title": "irrelevant"},
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            'Error': "Missing key in Asset: 'type'",
            'Asset': {'title': 'irrelevant'}
        })

    def test_unknown_type(self):
        response = self.client.post(reverse('save_asset'),
                                    data={"type": "nonexistent-type",
                                          "title": "irrelevant"},
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "Error": "Unknown AssetType: nonexistent-type",
            'Asset': {'title': 'irrelevant',
                      'type': 'nonexistent-type'}
        })

    def test_missing_key_from_schema(self):
        response = self.client.post(reverse('save_asset'),
                                    data={"type": "article",
                                          "title": "Missing subtitle",
                                          "abstract": "Foo",
                                          "author": "Max Mustermann",
                                          "content": []},
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "Error": "Missing key 'subtitle' in AssetType 'article'.",
            'Asset': {"type": "article",
                      "title": "Missing subtitle",
                      "abstract": "Foo",
                      "author": "Max Mustermann",
                      "content": []}
        })

    def test_error_in_sub_asset(self):
        response = self.client.post(reverse('save_asset'),
                                    data={"type": "article",
                                          "title": "Nice title",
                                          "subtitle": "More descriptive title for the web",
                                          "abstract": "Foo",
                                          "author": "Max Mustermann",
                                          "content": [
                                              {"type": "block-paragraph",
                                               "spans": [
                                                   {"type": "span-regular"}
                                               ]}
                                          ]},
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.maxDiff = None
        self.assertJSONEqual(response.content, {
            "Error": "Missing key 'text' in AssetType 'span-regular'.",
            'Asset': {"type":  "span-regular"}
        })

    def test_testilinio(self):
        with open(os.path.join("assets", "tests", "testilinio.json"), 'r') as json_file:
            testilinio_tree = json.load(json_file)
        response = self.client.post(reverse('save_asset'),
                                    data=testilinio_tree,
                                    content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            "Success": True
        })
