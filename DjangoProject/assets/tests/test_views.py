# -*- coding: utf-8 -*-
from django.test import TestCase
from django.test import Client
from django.urls import reverse
from assets.models import AssetType, Asset, Text, UriElement, Enum
import json
import os


class TestLoadAsset(TestCase):
    fixtures = [
        'span_assets.yaml',
        'caption-span_assets.yaml',
        'block_assets.yaml',
        'table.yaml',
        'enum_types.yaml'
    ]

    def setUp(self) -> None:
        self.client = Client()

    def test_no_params(self):
        response = self.client.get(reverse('load_asset'))
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            'Error': "Please supply a 'id' as a GET param."
        })

    def test_wrong_id(self):
        response = self.client.get(reverse('load_asset'),
                                   {"id": "cd1249e5-3955-4468-87be-d912e1adb2d9"})
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            'Error': "No Asset with id=cd1249e5-3955-4468-87be-d912e1adb2d9 found."
        })

    def test_load_block(self):
        title = Text(text="Text Box Title")
        title.save()
        content = Text(text="This is the content of the box.")
        content.save()
        span = Asset(t=AssetType.objects.get(type_name="span-regular"), content_ids={
            "text": content.pk
        })
        span.save()
        paragraph_block = Asset(t=AssetType.objects.get(type_name="block-paragraph"), content_ids={
            "spans": [str(span.pk)]
        })
        paragraph_block.save()
        box = Asset(t=AssetType.objects.get(type_name="block-accompaniement-box"), content_ids={
            "title": title.pk,
            "content": [str(paragraph_block.pk)]})
        box.save()
        response = self.client.get(reverse('load_asset'), {"id": str(box.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            "type": "block-accompaniement-box",
            "title": "Text Box Title",
            "id": str(box.pk),
            "content": [
                {"type": "block-paragraph",
                 "id": str(paragraph_block.pk),
                 "spans": [
                     {"type": "span-regular",
                      "id": str(span.pk),
                      "text": "This is the content of the box."}
                 ]}
            ]
        })


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
        self.assertJSONEqual(response.content, {
            "Error": "An Asset with id 412575db-7407-4de9-936f-050dd7827f59 does not exist.",
            "Asset": {"id": "412575db-7407-4de9-936f-050dd7827f59"}
        })

    def test_no_type_in_existing_sub_asset(self):
        text = Text(text="Foo")
        text.save()
        span = Asset(t=AssetType.objects.get(type_name="span-regular"),
                     content_ids={"text": text.pk})
        span.save()
        response = self.client.post(
            reverse('save_asset'),
            data={"type": "block-paragraph",
                  "spans": [
                      {"id": str(span.pk),
                       "text": "This is not 'Foo'"}
                 ]}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        block = Asset.objects.filter(content_ids__spans=[str(span.pk)])[0]
        self.assertJSONEqual(response.content, {
            "Success": True,
            "id": str(block.pk)
        })

    def test_illegal_block_in_block(self):
        response = self.client.post(
            reverse('save_asset'),
            data={"type": "block-paragraph",
                  "spans": [
                      {"type": "block-paragraph",
                       "text": "Foo"}
                  ]}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "Error": "Expected an AssetType with id 4 but got 'block-paragraph' with id 15.",
            "Asset": {'text': 'Foo', 'type': 'block-paragraph'}
        })

    def test_no_list_where_the_schema_demands_one(self):
        response = self.client.post(
            reverse('save_asset'),
            data={"type": "block-paragraph",
                  "spans": {"type": "span-regular",
                            "text": "Foo"}
                  }, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "Error": "The Schema of AssetType 'block-paragraph' demands the content for key 'spans' to be a List.",
            "Asset": {"type": "block-paragraph", "spans": {"type": "span-regular", "text": "Foo"}}
        })

    def test_list_instead_of_text(self):
        response = self.client.post(
            reverse('save_asset'),
            data={
                "type": "span-link",
                "link_text": ["foo"],
                "url": "https://ct.de"
            }, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "Error": "The Schema of AssetType 'span-link' demands the content for key 'link_text' to be a string.",
            "Asset": {'link_text': ['foo'], 'type': 'span-link', 'url': "https://ct.de"}
        })

    def test_dict_instead_of_url(self):
        response = self.client.post(
            reverse('save_asset'),
            data={
                "type": "span-link",
                "link_text": "foo",
                "url": {3: 2}
            }, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "Error": "The Schema of AssetType 'span-link' demands the content for key 'url' to be a string with a URI.",
            "Asset": {"link_text": "foo", "type": "span-link", "url": {"3": 2}}
        })

    def test_list_instead_of_asset(self):
        response = self.client.post(
            reverse('save_asset'),
            data={
                "type": "block-paragraph",
                "spans": ["foo"]
            }, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "Error": "The Schema of AssetType 'block-paragraph' demands the content for key 'spans' to be an Asset. " +
                     "Assets are saved as JSON-objects with an inner structure matching the schema of their type.",
            "Asset": "foo"
        })

    def test_create_url(self):
        response = self.client.post(
            reverse('save_asset'),
            data={
                "type": "span-link",
                "link_text": "foo",
                "url": "https://ct.de/lksadhla"
            }, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        uri_object = UriElement.objects.filter(uri="https://ct.de/lksadhla")[0]
        asset = Asset.objects.get(content_ids__url=uri_object.pk)
        self.assertJSONEqual(response.content, {
            "Success": True,
            "id": str(asset.pk)
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

    def test_modify_uri(self):
        response = self.client.post(
            reverse('save_asset'),
            data={"type": "block-paragraph",
                  "spans": [
                      {"type": "span-link",
                       "link_text": "Foo",
                       "url": "https://unittest.com/sGa2Jk3l7fLj"}
                  ]},
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            "Success": True,
            "id": json.loads(response.content)["id"]
        })
        asset = Asset.objects.get(pk=json.loads(response.content)["id"])
        span_link = Asset.objects.get(pk=asset.content_ids["spans"][0])
        response = self.client.post(
            reverse('save_asset'),
            data={"id": str(asset.pk),
                  "type": "block-paragraph",
                  "spans": [
                      {"id": str(span_link.pk),
                       "url": "https://changed.to/H6Ld5s2pU0"}
                  ]},
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            "Success": True,
            "id": str(asset.pk)
        })
        asset_reloaded = Asset.objects.get(pk=asset.pk)
        span_link_reloaded = Asset.objects.get(pk=span_link.pk)
        self.assertJSONEqual(json.dumps(asset_reloaded.content), json.dumps({
            "type": "block-paragraph",
            "id": str(asset_reloaded.pk),
            "spans": [
                {"id": str(span_link_reloaded.pk),
                 "type": "span-link",
                 "link_text": "Foo",
                 "url": "https://changed.to/H6Ld5s2pU0"}
            ]
        }))
        self.assertIsNotNone(span_link_reloaded.revision_chain)
        self.assertEqual(UriElement.objects.count(), 2)
        self.assertEqual(
            span_link_reloaded.content_ids["url"],
            UriElement.objects.filter(uri="https://changed.to/H6Ld5s2pU0")[0].pk)
        self.assertEqual(
            span_link_reloaded.revision_chain.content_ids["url"],
            UriElement.objects.filter(uri="https://unittest.com/sGa2Jk3l7fLj")[0].pk)

    def test_modify_enum(self):
        response = self.client.post(
            reverse('save_asset'),
            data={"type": "block-info-box",
                  "title": "Box title",
                  "content": [
                      {"type": "block-listing",
                       "language": "python",
                       "code": "print(1)"}
                  ]},
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            "Success": True,
            "id": json.loads(response.content)["id"]
        })
        box = Asset.objects.get(pk=json.loads(response.content)["id"])
        block_listing = Asset.objects.get(pk=box.content_ids["content"][0])
        response = self.client.post(
            reverse('save_asset'),
            data={"id": str(box.pk),
                  "type": "block-info-box",
                  "title": "Box title",
                  "content": [
                      {"id": str(block_listing.pk),
                       "type": "block-listing",
                       "language": "kotlin",
                       "code": "print(1)"}
                  ]},
            content_type="application/json")
        self.assertJSONEqual(response.content, {
            "Success": True,
            "id": str(box.pk)
        })
        box_reloaded = Asset.objects.get(pk=box.pk)
        block_listing_reloaded = Asset.objects.get(pk=block_listing.pk)
        self.assertJSONEqual(json.dumps(box_reloaded.content), json.dumps({
            "id": str(box_reloaded.pk),
            "type": "block-info-box",
            "title": "Box title",
            "content": [
                {"id": str(block_listing_reloaded.pk),
                 "type": "block-listing",
                 "language": "kotlin",
                 "code": "print(1)"}
            ]
        }))
        self.assertIsNotNone(block_listing_reloaded.revision_chain)
        self.assertEqual(Enum.objects.count(), 2)
        self.assertEqual(
            block_listing_reloaded.content_ids["language"],
            Enum.objects.filter(item="kotlin")[0].pk)
        self.assertEqual(
            block_listing_reloaded.revision_chain.content_ids["language"],
            Enum.objects.filter(item="python")[0].pk)

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
