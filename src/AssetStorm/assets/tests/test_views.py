# -*- coding: utf-8 -*-
from django.test import TestCase
from django.test import Client
from test.support import EnvironmentVarGuard
from django.urls import reverse
from django.core.management import call_command
from AssetStorm.assets.models import AssetType, Asset, Text, UriElement, Enum, EnumType
from AssetStorm.urls import urlpatterns
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
            "success": True,
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
            "success": True,
            "id": str(asset.pk)
        })

    def test_unknown_enum_type(self):
        enum_test_asset_type = AssetType(type_name="enum-test", schema={
            "enum": {"3": 3}
        })
        enum_test_asset_type.save()
        response = self.client.post(reverse('save_asset'), data={
                "type": "enum-test",
                "enum": "tuiornuidtaeosuien"
            }, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "Error": "Unknown EnumType: tuiornuidtaeosuien.",
            "Asset": {"type": "enum-test",
                      "enum": "tuiornuidtaeosuien"}
        })

    def test_unknown_enum(self):
        enum_test_type = EnumType(items=["a", "b", "c"])
        enum_test_type.save()
        enum_test_asset_type = AssetType(type_name="enum-test", schema={
            "enum": {"3": enum_test_type.pk}
        })
        enum_test_asset_type.save()
        response = self.client.post(reverse('save_asset'), data={
                "type": "enum-test",
                "enum": "d"
            }, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "Error": "The Schema of AssetType 'enum-test' demands the content for key 'enum' " +
                     "to be the enum_type with id=%d." % enum_test_type.pk,
            "Asset": {"type": "enum-test",
                      "enum": "d"}
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
            "success": True,
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
            "success": True,
            "id": str(asset.pk)
        })
        modified_asset = Asset.objects.get(pk=json.loads(response2.content)["id"])
        self.assertEqual(modified_asset.pk, asset.pk)
        modified_span = Asset.objects.get(pk=modified_asset.content_ids["spans"][0])
        modified_text = Text.objects.get(text="This text is changed.")
        self.assertEqual(modified_span.content_ids["text"], modified_text.pk)
        self.assertEqual(modified_asset.content_ids["spans"][0],
                         str(modified_span.pk))
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
            "success": True,
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
            "success": True,
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
            "success": True,
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
            "success": True,
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

    def test_modify_list_order(self):
        response = self.client.post(
            reverse('save_asset'),
            data={"type": "block-paragraph",
                  "spans": [
                      {"type": "span-regular", "text": "a"},
                      {"type": "span-regular", "text": "b"}
                  ]},
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            "success": True,
            "id": json.loads(response.content)["id"]
        })
        asset = Asset.objects.get(pk=json.loads(response.content)["id"])
        self.assertJSONEqual(json.dumps(asset.content), json.dumps({
            "id": str(asset.pk),
            "type": "block-paragraph",
            "spans": [
                {"id": str(asset.content_ids["spans"][0]), "type": "span-regular", "text": "a"},
                {"id": str(asset.content_ids["spans"][1]), "type": "span-regular", "text": "b"}
            ]
        }))
        response = self.client.post(
            reverse('save_asset'),
            data={"id": str(asset.pk),
                  "type": "block-paragraph",
                  "spans": [
                      {"id": str(asset.content_ids["spans"][1])},
                      {"id": str(asset.content_ids["spans"][0])}
                  ]},
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            "success": True,
            "id": str(asset.pk)
        })
        asset_reloaded = Asset.objects.get(pk=asset.pk)
        self.assertJSONEqual(json.dumps(asset_reloaded.content), json.dumps({
            "id": str(asset_reloaded.pk),
            "type": "block-paragraph",
            "spans": [
                {"id": str(asset_reloaded.content_ids["spans"][0]), "type": "span-regular", "text": "b"},
                {"id": str(asset_reloaded.content_ids["spans"][1]), "type": "span-regular", "text": "a"}
            ]
        }))
        self.assertIsNotNone(asset_reloaded.revision_chain)
        a = Asset.objects.get(
            new_version=None,
            content_ids__text=Text.objects.get(text="a").pk)
        self.assertIsNone(a.revision_chain)
        b = Asset.objects.get(
            new_version=None,
            content_ids__text=Text.objects.get(text="b").pk)
        self.assertIsNone(a.revision_chain)
        self.assertEqual(asset_reloaded.content_ids["spans"][0], str(b.pk))
        self.assertEqual(asset_reloaded.content_ids["spans"][1], str(a.pk))
        self.assertEqual(asset_reloaded.revision_chain.content_ids["spans"][0], str(a.pk))
        self.assertEqual(asset_reloaded.revision_chain.content_ids["spans"][1], str(b.pk))

    def test_listless_sub_asset_change(self):
        block_singleblock = AssetType(type_name="block-singleblock", schema={"block": 5},
                                      parent_type=AssetType.objects.get(type_name="block"))
        block_singleblock.save()
        response = self.client.post(
            reverse('save_asset'),
            data={"type": "block-singleblock",
                  "block": {
                      "type": "block-listing",
                      "language": "python",
                      "code": "print(1)"}},
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            "success": True,
            "id": json.loads(response.content)["id"]
        })
        asset = Asset.objects.get(pk=json.loads(response.content)["id"])
        self.assertEqual(asset.t, block_singleblock)
        self.assertJSONEqual(json.dumps(asset.content), json.dumps({
            "id": str(asset.pk),
            "type": "block-singleblock",
            "block": {
                "id": asset.content_ids["block"],
                "type": "block-listing",
                "language": "python",
                "code": "print(1)"}
        }))
        tree = asset.content.copy()
        tree["block"]["language"] = "kotlin"
        response = self.client.post(
            reverse('save_asset'),
            data=tree,
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            "success": True,
            "id": str(asset.pk)
        })
        asset_reloaded = Asset.objects.get(pk=asset.pk)
        listing_block = Asset.objects.get(pk=asset_reloaded.content_ids["block"])
        self.assertJSONEqual(json.dumps(asset_reloaded.content), json.dumps({
            "type": "block-singleblock",
            "id": str(asset_reloaded.pk),
            "block": {
                "type": "block-listing",
                "id": str(listing_block.pk),
                "code": "print(1)",
                "language": "kotlin"}}))
        self.assertIsNone(asset_reloaded.revision_chain)
        self.assertIsNotNone(listing_block.revision_chain)
        self.assertEqual(listing_block.content_ids["language"], Enum.objects.get(item="kotlin").pk)
        tree["block"] = {"type": "block-paragraph", "spans": [
            {"type": "span-regular", "text": "Foobar Baz!"}
        ]}
        response = self.client.post(
            reverse('save_asset'),
            data=tree,
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            "success": True,
            "id": str(asset.pk)
        })
        asset_reloaded2 = Asset.objects.get(pk=asset.pk)
        paragraph_block = Asset.objects.get(pk=asset_reloaded2.content_ids["block"])
        self.assertIsNotNone(asset_reloaded2.revision_chain)
        self.assertJSONEqual(json.dumps(asset_reloaded2.content), json.dumps({
            "id": str(asset_reloaded2.pk),
            "type": "block-singleblock",
            "block": {
                "id": str(paragraph_block.pk),
                "type": "block-paragraph",
                "spans": [{"id": paragraph_block.content_ids["spans"][0],
                           "type": "span-regular",
                           "text": "Foobar Baz!"}]}
        }))

    def test_testilinio(self):
        with open(os.path.join(os.path.dirname(__file__), "testilinio.json"), 'r') as json_file:
            testilinio_tree = json.load(json_file)
        response = self.client.post(reverse('save_asset'),
                                    data=testilinio_tree,
                                    content_type="application/json")
        self.assertEqual(response.status_code, 200)
        title = Text.objects.get(text="Testilinio")
        article_asset = Asset.objects.get(content_ids__title=title.pk)
        self.assertJSONEqual(response.content, {
            "success": True,
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


class TestTurnoutView(TestCase):
    fixtures = [
        'span_assets.yaml',
        'caption-span_assets.yaml',
        'block_assets.yaml',
        'table.yaml',
        'enum_types.yaml'
    ]

    def setUp(self) -> None:
        self.client = Client()

    def test_load(self):
        code = Text(text="print(1)")
        code.save()
        lang_python = Enum(t=EnumType.objects.get(pk=2), item="python")
        lang_python.save()
        listing_block = Asset(t=AssetType.objects.get(type_name="block-listing"), content_ids={
            "code": code.pk,
            "language": lang_python.pk
        })
        listing_block.save()
        response = self.client.get(reverse('turnout_request'), {'id': str(listing_block.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json.dumps({
            "id": str(listing_block.pk),
            "type": "block-listing",
            "code": "print(1)",
            "language": "python"
        }))

    def test_save(self):
        response = self.client.post(reverse('turnout_request'), data={
            "type": "block-listing",
            "code": "print(1)",
            "language": "python"
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        saved_asset = Asset.objects.get(pk=json.loads(response.content)["id"])
        self.assertJSONEqual(response.content, json.dumps({
            "success": True,
            "id": str(saved_asset.pk)
        }))
        self.assertJSONEqual(json.dumps(saved_asset.content), json.dumps({
            "id": str(saved_asset.pk),
            "type": "block-listing",
            "code": "print(1)",
            "language": "python"
        }))


class TestQueryView(TestCase):
    fixtures = [
        'span_assets.yaml',
        'caption-span_assets.yaml',
        'block_assets.yaml',
        'table.yaml',
        'enum_types.yaml'
    ]

    def setUp(self) -> None:
        self.client = Client()

    def test_filter_not_json(self):
        response = self.client.post(
            reverse("find_assets", args={"query_string": "foo"}),
            data="{argh: 2]", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), {
            "Error": "The filters are not in JSON format. The request body has to be valid JSON."
        })

    def test_wrong_content_type(self):
        response = self.client.post(
            reverse("filter_assets"),
            data="{\"key\": \"value\"}", content_type="text/html")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content),
                         {"Error": "If you supply filters they need to be valid JSON " +
                                   "and the request must have the MIME-type \"application/json\"."})

    def test_wrong_content_type_but_empty_body(self):
        response = self.client.post(
            reverse("filter_assets"),
            data="", content_type="text/html")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content),
                         {"assets": []})

    def test_filter_empty(self):
        response = self.client.post(
            reverse("filter_assets"),
            data=None, content_type="application/json")
        self.assertEqual(response.status_code, 200)

    def test_search_over_two_assets(self):
        save_response = self.client.post(reverse("save_asset"), data={
            "type": "block-info-box",
            "title": "Box from test",
            "content": [
                {"type": "block-paragraph",
                 "spans": [
                     {"type": "span-regular",
                      "text": "This is the text "},
                     {"type": "span-strong",
                      "text": "you"},
                     {"type": "span-regular",
                      "text": " are searching for!"}
                 ]}
            ]
        }, content_type="application/json")
        call_command("build_caches")
        box = Asset.objects.get(pk=json.loads(save_response.content)["id"])
        find_response = self.client.post(reverse("find_assets", args=("text you",)),
                                         data=None, content_type="application/json")
        found_assets = json.loads(find_response.content)["assets"]
        self.assertEqual(len(found_assets), 2)
        self.assertIn({
            "id": str(box.pk),
            "type_id": box.t.pk,
            "raw_content_snippet": box.raw_content_cache[:500]
        }, found_assets)
        parapgraph = Asset.objects.get(pk=box.content_ids["content"][0])
        self.assertIn({
            "id": str(parapgraph.pk),
            "type_id": parapgraph.t.pk,
            "raw_content_snippet": parapgraph.raw_content_cache[:500]
        }, found_assets)

    def test_search_over_two_assets_with_filter(self):
        save_response = self.client.post(reverse("save_asset"), data={
            "type": "block-info-box",
            "title": "Box from test",
            "content": [
                {"type": "block-paragraph",
                 "spans": [
                     {"type": "span-regular",
                      "text": "This is the text "},
                     {"type": "span-strong",
                      "text": "you"},
                     {"type": "span-regular",
                      "text": " are searching for!"}
                 ]}
            ]
        }, content_type="application/json")
        call_command("build_caches")
        box = Asset.objects.get(pk=json.loads(save_response.content)["id"])
        find_response = self.client.post(
            reverse("find_assets", args=("text you",)),
            data={
                "type": "block-info-box"
            }, content_type="application/json")
        found_assets = json.loads(find_response.content)["assets"]
        self.assertEqual(len(found_assets), 1)
        self.assertIn({
            "id": str(box.pk),
            "type_id": box.t.pk,
            "raw_content_snippet": box.raw_content_cache[:500]
        }, found_assets)


class TestGetTemplateView(TestCase):
    def setUp(self) -> None:
        self.client = Client()

    def test_no_params(self):
        error_response = self.client.get(reverse("get_template"))
        self.assertEqual(400, error_response.status_code)
        self.assertEqual("application/json", error_response['content-type'])
        self.assertEqual({"Error": "You must supply template_type and type_name as GET params."},
                         json.loads(error_response.content))

    def test_non_existent_asset_type(self):
        error_response = self.client.get(reverse("get_template"), data={
            "type_name": "illegal_type", "template_type": "proof_html"})
        self.assertEqual(400, error_response.status_code)
        self.assertEqual("application/json", error_response['content-type'])
        self.assertEqual({"Error": "The AssetType \"illegal_type\" does not exist."},
                         json.loads(error_response.content))

    def test_non_existent_template_type(self):
        foo = AssetType(type_name="foo", schema={"key": 1}, templates={"raw": "{{key}}"})
        foo.save()
        error_response = self.client.get(reverse("get_template"), data={
            "type_name": "foo", "template_type": "proof_html"})
        self.assertEqual(400, error_response.status_code)
        self.assertEqual("application/json", error_response['content-type'])
        self.assertEqual({"Error": "The AssetType \"foo\" has no template \"proof_html\"."},
                         json.loads(error_response.content))

    def test_successful_request(self):
        foo = AssetType(type_name="foo", schema={"key": 1}, templates={
            "raw": "{{key}}",
            "proof_html": "<div class=\"foo\">{{key}}</div>"})
        foo.save()
        response = self.client.get(reverse("get_template"), data={
            "type_name": "foo", "template_type": "proof_html"})
        self.assertEqual(200, response.status_code)
        self.assertEqual("utf-8", response.charset)
        self.assertEqual("text/plain", response['content-type'])
        self.assertEqual("<div class=\"foo\">{{key}}</div>",
                         str(response.content, encoding="utf-8"))


class TestDeliverOpenApiDefinition(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.env = EnvironmentVarGuard()

    def test_default_first_server(self):
        response = self.client.get(reverse("openapi.json"))
        self.assertEqual(200, response.status_code)
        self.assertEqual("application/json", response['content-type'])
        api_def = json.loads(response.content)
        self.assertEqual('3.0.0', api_def['openapi'])
        self.assertEqual('AssetStorm', api_def['info']['title'])
        self.assertEqual({'url': 'http://assetstorm.pinae.net'}, api_def['servers'][0])
        for url in urlpatterns:
            pattern = '/' + str(url.pattern).replace('<str:', '{').replace('>', '}')
            self.assertIn(pattern, api_def['paths'])

    def test_server_by_env(self):
        self.env.set('SERVER_NAME', 'https://test.org/foo/bar/baz')
        with self.env:
            response = self.client.get(reverse("openapi.json"))
            self.assertEqual(200, response.status_code)
            self.assertEqual("application/json", response['content-type'])
            api_def = json.loads(response.content)
            self.assertEqual({'url': 'https://test.org/foo/bar/baz'}, api_def['servers'][0])
