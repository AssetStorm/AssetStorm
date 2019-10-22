# -*- coding: utf-8 -*-
from django.test import TestCase
from django.test import Client
from django.urls import reverse
from assets.models import AssetType, Asset, Text
import json
import os


class TestSaveAsset(TestCase):
    fixtures = [
        'span_assets.yaml',
        'caption-span_assets.yaml',
        'block_assets.yaml',
        'table.yaml',
        'enum_types.yaml'
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

    def test_unknown_language_in_listing(self):
        response = self.client.post(reverse('save_asset'),
                                    data={"type": "article",
                                          "title": "Nice title",
                                          "subtitle": "More descriptive title for the web",
                                          "abstract": "Foo",
                                          "author": "Max Mustermann",
                                          "content": [
                                              {"type": "block-paragraph",
                                               "spans": [
                                                   {"type": "span-regular",
                                                    "text": "This is some text at the beginning of the article"}
                                               ]},
                                              {"type": "block-listing",
                                               "language": "unknown",
                                               "code": "print(str(12))\nfor i in range(5):\n  print(i)"}
                                          ]},
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "Error": "The Schema of AssetType 'block-listing' demands the content " +
                     "for key 'language' to be the enum_type with id=2.",
            'Asset': {"type":  "block-listing",
                      "language": "unknown",
                      "code": "print(str(12))\nfor i in range(5):\n  print(i)"}
        })

    def test_invalid_asset_id(self):
        response = self.client.post(reverse('save_asset'),
                                    data={"id": "foo"},
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "Error": "The id 'foo' is not a valid uuid (v4).",
            "Asset": {"id": "foo"}
        })

    def test_unknown_asset_id(self):
        response = self.client.post(reverse('save_asset'),
                                    data={"id": "412575db-7407-4de9-936f-050dd7827f59"},
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.maxDiff = None
        self.assertJSONEqual(response.content, {
            "Error": "An Asset with id 412575db-7407-4de9-936f-050dd7827f59 does not exist.",
            "Asset": {"id": "412575db-7407-4de9-936f-050dd7827f59"}
        })

    def test_modify_asset(self):
        response = self.client.post(
            reverse('save_asset'),
            data={"type": "block-paragraph",
                  "spans": [
                      {"type": "span-regular",
                       "text": "This is some text at the beginning of the article"}
                  ]},
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            "Success": True,
            "id": json.loads(response.content)["id"]
        })
        asset = Asset.objects.get(pk=json.loads(response.content)["id"])
        self.assertEqual(asset.content["spans"][0]["text"], "This is some text at the beginning of the article")
        json_content = asset.content.copy()
        json_content["spans"][0]["text"] = "This text is changed."
        response2 = self.client.post(
            reverse('save_asset'),
            data=json_content,
            content_type="application/json")
        self.assertEqual(response2.status_code, 200)
        self.assertJSONEqual(response2.content, {
            "Success": True,
            "id": str(asset.pk)
        })
        modified_asset = Asset.objects.get(pk=json.loads(response2.content)["id"])
        self.assertEqual(modified_asset.pk, asset.pk)
        self.assertEqual(modified_asset.content["spans"][0]["text"], "This text is changed.")

    def test_testilinio(self):
        with open(os.path.join("assets", "tests", "testilinio.json"), 'r') as json_file:
            testilinio_tree = json.load(json_file)
        response = self.client.post(reverse('save_asset'),
                                    data=testilinio_tree,
                                    content_type="application/json")
        self.assertEqual(response.status_code, 200)
        title = Text.objects.get(text="Testilinio")
        article_asset = Asset.objects.get(content_ids__title=title.pk)
        self.assertJSONEqual(response.content, {
            "Success": True,
            "id": str(article_asset.pk)
        })
        check_tree = testilinio_tree.copy()
        check_tree["id"] = str(article_asset.pk)
        for i, block_id in enumerate(article_asset.content_ids["content"]):
            block_asset = Asset.objects.get(pk=block_id)
            if block_asset.t.type_name == "block-paragraph":
                for j, span_id in enumerate(block_asset.content_ids["spans"]):
                    span_asset = Asset.objects.get(pk=span_id)
                    check_tree["content"][i]["spans"][j]["id"] = str(span_asset.pk)
            check_tree["content"][i]["id"] = str(block_asset.pk)
        self.assertJSONEqual(json.dumps(article_asset.content), json.dumps(check_tree))
