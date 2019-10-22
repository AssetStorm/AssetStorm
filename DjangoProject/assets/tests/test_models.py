# -*- coding: utf-8 -*-
from django.test import TestCase
from assets.models import AssetType, EnumType, Asset, Text, UriElement, Enum
import json
import uuid


class AssetBasicTestCase(TestCase):
    fixtures = [
        'span_assets.yaml',
        'caption-span_assets.yaml',
        'block_assets.yaml',
        'table.yaml',
        'enum_types.yaml'
    ]

    def at(self, type_name):
        return AssetType.objects.get(type_name=type_name)

    def setUp(self):
        article = AssetType(type_name="article", schema={
            "title": 1,
            "content": [self.at("block").pk]
        })
        article.save()

    def test_foo(self):
        t1 = Text(text="Foo")
        t1.save()
        t1_span = Asset(t=self.at("span-regular"), content_ids={"text": t1.pk})
        t1_span.save()
        self.assertJSONEqual(json.dumps(t1_span.content), json.dumps({
            'type': "span-regular",
            'id': str(t1_span.pk),
            'text': "Foo"
        }))

    def test_createAsset(self):
        title = Text(text="Funny Title")
        title.save()
        intro_text = Text(text="This is the beginning of the article.")
        intro_text.save()
        intro_span = Asset(t=self.at("span-regular"), content_ids={"text": intro_text.pk})
        intro_span.save()
        intro = Asset(t=self.at("block-paragraph"), content_ids={"spans": [str(intro_span.pk)]})
        intro.save()
        end_text1 = Text(text="This is the ")
        end_text1.save()
        end_span1 = Asset(t=self.at("span-regular"), content_ids={"text": end_text1.pk})
        end_span1.save()
        end_text2 = Text(text="end")
        end_text2.save()
        end_span2 = Asset(t=self.at("span-emphasized"), content_ids={"text": end_text2.pk})
        end_span2.save()
        end_text3 = Text(text=" of the article.")
        end_text3.save()
        end_span3 = Asset(t=self.at("span-regular"), content_ids={"text": end_text3.pk})
        end_span3.save()
        end = Asset(t=self.at("block-paragraph"), content_ids={"spans": [
            str(end_span1.pk),
            str(end_span2.pk),
            str(end_span3.pk)]})
        end.save()
        a = Asset(t=self.at("article"), content_ids={
            "title": str(title.pk),
            "content": [str(intro.pk), str(end.pk)]
        })
        a.save()
        print(json.dumps(a.content, indent=2))
        self.assertJSONEqual(json.dumps(a.content), json.dumps({
            "type": "article",
            "id": str(a.pk),
            "title": "Funny Title",
            "content": [
                {"type": "block-paragraph", "id": str(intro.pk), "spans": [
                    {"type": "span-regular", "id": str(intro_span.pk), "text": "This is the beginning of the article."}
                ]},
                {"type": "block-paragraph", "id": str(end.pk), "spans": [
                    {"type": "span-regular", "id": str(end_span1.pk), "text": "This is the "},
                    {"type": "span-emphasized", "id": str(end_span2.pk), "text": "end"},
                    {"type": "span-regular", "id": str(end_span3.pk), "text": " of the article."}
                ]}
            ]
        }))

    def test_listing_block(self):
        title = Text(text="Box Title")
        title.save()
        code = Text(text="a = 2 + 4\nprint(a)")
        code.save()
        language_type = EnumType.objects.get(pk=2)
        language = Enum(t=language_type, item="python")
        language.save()
        listing_block = Asset(t=self.at("block-listing"), content_ids={
            "language": language.pk,
            "code": code.pk
        })
        listing_block.save()
        box = Asset(t=self.at("block-accompaniement-box"), content_ids={
            "title": title.pk,
            "content": [str(listing_block.pk)]})
        box.save()
        print(json.dumps(box.content, indent=2))
