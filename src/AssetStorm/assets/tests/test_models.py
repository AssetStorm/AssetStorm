# -*- coding: utf-8 -*-
from django.test import TestCase
from AssetStorm.assets.models import AssetType, EnumType, Asset, Text, UriElement, Enum
import json


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
        self.assertJSONEqual(json.dumps(box.content), json.dumps({
            "type": "block-accompaniement-box",
            "id": str(box.pk),
            "title": "Box Title",
            "content": [
                {
                    "type": "block-listing",
                    "id": str(listing_block.pk),
                    "code": "a = 2 + 4\nprint(a)",
                    "language": "python"
                }
            ]
        }))

    def test_span_link(self):
        start = Text(text="In this sentence is a ")
        start.save()
        link_text = Text(text="link")
        link_text.save()
        link_target = UriElement(uri="https://ct.de")
        link_target.save()
        end = Text(text=" which leads to https://ct.de.")
        end.save()
        start_span = Asset(t=self.at("span-regular"), content_ids={"text": start.pk})
        start_span.save()
        link_span = Asset(t=self.at("span-link"), content_ids={"link_text": link_text.pk, "url": link_target.pk})
        link_span.save()
        end_span = Asset(t=self.at("span-regular"), content_ids={"text": end.pk})
        end_span.save()
        paragraph = Asset(t=self.at("block-paragraph"), content_ids={"spans": [
            str(start_span.pk),
            str(link_span.pk),
            str(end_span.pk)]})
        paragraph.save()
        self.maxDiff = None
        self.assertJSONEqual(json.dumps(paragraph.content), json.dumps({
            "type": "block-paragraph",
            "id": str(paragraph.pk),
            "spans": [
                {"type": "span-regular",
                 "id": str(start_span.pk),
                 "text": "In this sentence is a "},
                {"type": "span-link",
                 "id": str(link_span.pk),
                 "link_text": "link",
                 "url": "https://ct.de"},
                {"type": "span-regular",
                 "id": str(end_span.pk),
                 "text": " which leads to https://ct.de."},
            ]
        }))

    def test_cache_usage(self):
        text = Text(text="cached span")
        text.save()
        text_span = Asset(t=self.at("span-regular"), content_ids={"text": text.pk})
        text_span.save()
        self.assertIsNone(text_span.content_cache)
        expected_content = json.dumps({
            'type': "span-regular",
            'id': str(text_span.pk),
            'text': "cached span"
        })
        self.assertJSONEqual(json.dumps(text_span.content), expected_content)
        self.assertIsNotNone(text_span.content_cache)
        self.assertJSONEqual(json.dumps(text_span.content_cache), expected_content)
        self.assertJSONEqual(json.dumps(text_span.content), expected_content)

    def test_clear_cache(self):
        text = Text(text="cached text")
        text.save()
        span = Asset(t=self.at("span-regular"), content_ids={"text": text.pk})
        span.save()
        block = Asset(t=self.at("block-paragraph"), content_ids={"spans": [str(span.pk)]})
        block.save()
        self.assertIsNone(span.content_cache)
        self.assertIsNone(block.content_cache)
        self.assertJSONEqual(json.dumps(span.content), json.dumps({
            'type': "span-regular",
            'id': str(span.pk),
            'text': "cached text"
        }))
        self.assertJSONEqual(json.dumps(block.content), json.dumps({
            'type': "block-paragraph",
            'id': str(block.pk),
            'spans': [
                {'type': "span-regular",
                 'id': str(span.pk),
                 'text': "cached text"}
            ]
        }))
        span = Asset.objects.get(pk=span.pk)
        block = Asset.objects.get(pk=block.pk)
        self.assertIsNotNone(span.content_cache)
        self.assertIsNotNone(block.content_cache)
        span.clear_cache()
        span = Asset.objects.get(pk=span.pk)
        block = Asset.objects.get(pk=block.pk)
        self.assertIsNone(span.content_cache)
        self.assertIsNone(block.content_cache)

    def test_reference_lists(self):
        text = Text(text="text in span and a ")
        text.save()
        text_span = Asset(t=self.at("span-regular"), content_ids={"text": text.pk})
        text_span.save()
        link_text = Text(text="link text.")
        link_text.save()
        link_url = UriElement(uri="https://ct.de")
        link_url.save()
        link_span = Asset(t=self.at("span-link"), content_ids={"link_text": link_text.pk, "url": link_url.pk})
        link_span.save()
        text_block = Asset(t=self.at("block-paragraph"), content_ids={"spans": [str(text_span.pk), str(link_span.pk)]})
        text_block.save()
        code = Text(text="a = 2 + 1\nprint(a == 3)")
        code.save()
        code_lang = Enum(t=EnumType.objects.get(pk=2), item="python")
        code_lang.save()
        listing_block = Asset(t=self.at("block-listing"), content_ids={"language": code_lang.pk, "code": code.pk})
        listing_block.save()
        box_heading = Text(text="Box heading")
        box_heading.save()
        box = Asset(t=self.at("block-info-box"), content_ids={
            "title": box_heading.pk,
            "content": [str(text_block.pk), str(listing_block.pk)]})
        box.save()
        self.assertJSONEqual(json.dumps(box.content), json.dumps({
            "type": "block-info-box",
            "id": str(box.pk),
            "title": "Box heading",
            "content": [
                {
                    "type": "block-paragraph",
                    "id": str(text_block.pk),
                    "spans": [
                        {
                            "type": "span-regular",
                            "id": str(text_span.pk),
                            "text": "text in span and a "
                        },
                        {
                            "type": "span-link",
                            "id": str(link_span.pk),
                            "url": "https://ct.de",
                            "link_text": "link text."
                        }
                    ]
                },
                {
                    "type": "block-listing",
                    "id": str(listing_block.pk),
                    "code": "a = 2 + 1\nprint(a == 3)",
                    "language": "python"
                }
            ]
        }))
        text_block = Asset.objects.get(pk=text_block.pk)
        listing_block = Asset.objects.get(pk=listing_block.pk)
        text_span = Asset.objects.get(pk=text_span.pk)
        link_span = Asset.objects.get(pk=link_span.pk)
        self.assertIn(text_block.pk, box.asset_reference_list)
        self.assertIn(listing_block.pk, box.asset_reference_list)
        self.assertNotIn(text_span.pk, box.asset_reference_list)
        self.assertNotIn(link_span.pk, box.asset_reference_list)
        self.assertIn(box_heading.pk, box.text_reference_list)
        self.assertNotIn(link_text.pk, box.text_reference_list)
        self.assertEqual(len(box.text_reference_list), 1)
        self.assertEqual(len(box.uri_reference_list), 0)
        self.assertEqual(len(box.enum_reference_list), 0)
        self.assertEqual(len(box.asset_reference_list), 2)
        self.assertIn(text_span.pk, text_block.asset_reference_list)
        self.assertIn(link_span.pk, text_block.asset_reference_list)
        self.assertEqual(len(text_block.text_reference_list), 0)
        self.assertEqual(len(text_block.uri_reference_list), 0)
        self.assertEqual(len(text_block.enum_reference_list), 0)
        self.assertEqual(len(text_block.asset_reference_list), 2)
        self.assertIn(code.pk, listing_block.text_reference_list)
        self.assertIn(code_lang.pk, listing_block.enum_reference_list)
        self.assertEqual(len(listing_block.text_reference_list), 1)
        self.assertEqual(len(listing_block.uri_reference_list), 0)
        self.assertEqual(len(listing_block.enum_reference_list), 1)
        self.assertEqual(len(listing_block.asset_reference_list), 0)
        self.assertIn(text.pk, text_span.text_reference_list)
        self.assertEqual(len(text_span.text_reference_list), 1)
        self.assertEqual(len(text_span.uri_reference_list), 0)
        self.assertEqual(len(text_span.enum_reference_list), 0)
        self.assertEqual(len(text_span.asset_reference_list), 0)
        self.assertIn(link_text.pk, link_span.text_reference_list)
        self.assertIn(link_url.pk, link_span.uri_reference_list)
        self.assertEqual(len(link_span.text_reference_list), 1)
        self.assertEqual(len(link_span.uri_reference_list), 1)
        self.assertEqual(len(link_span.enum_reference_list), 0)
        self.assertEqual(len(link_span.asset_reference_list), 0)


class RawTemplateTests(TestCase):
    fixtures = [
        'span_assets.yaml',
        'caption-span_assets.yaml',
        'block_assets.yaml',
        'table.yaml',
        'enum_types.yaml'
    ]

    def test_no_raw_template(self):
        insufficient_type = AssetType(type_name="insufficient_type", schema={"text": 1}, templates={})
        insufficient_type.save()
        t = Text(text="Foobar!")
        t.save()
        asset = Asset(t=insufficient_type, content_ids={
            "text": t.pk
        })
        asset.save()
        self.assertEqual(asset.render_template(), "")

    def test_basic_template(self):
        statement = Text(text="Vertrauen ist gut. Kontrolle ist besser.")
        statement.save()
        attribution = Text(text="Lenin")
        attribution.save()
        asset = Asset(t=AssetType.objects.get(type_name="block-citation"), content_ids={
            "statement": statement.pk, "attribution": attribution.pk
        })
        asset.save()
        self.assertEqual(asset.render_template(), "Vertrauen ist gut. Kontrolle ist besser.\n - Lenin\n")

    def test_text_list_template(self):
        ul = AssetType(type_name="ul", schema={"texts": [1]}, templates={
            "raw": "{{for(texts)}} - {{texts}}\n{{endfor}}",
            "html": "<ul>{{for(texts)}}\n  <li>{{texts}}</li>{{endfor}}\n</ul>"
        })
        ul.save()
        t1 = Text(text="Foo")
        t1.save()
        t2 = Text(text="Bar")
        t2.save()
        t3 = Text(text="Baz")
        t3.save()
        asset = Asset(t=ul, content_ids={"texts": [t1.pk, t2.pk, t3.pk]})
        asset.save()
        self.assertEqual(asset.render_template("html"), "<ul>\n  <li>Foo</li>\n  <li>Bar</li>\n  <li>Baz</li>\n</ul>")
        self.assertEqual(asset.render_template(), " - Foo\n - Bar\n - Baz\n")

    def test_asset_all_types_template(self):
        all_type = AssetType(type_name="all_type", schema={
            "text": 1,
            "url": 2,
            "enum": {"3": 2},
            "asset": 4,
            "texts": [1],
            "urls": [2],
            "enums": [{"3": 2}],
            "assets": [4]
        }, templates={
            "raw": """
            text: {{text}}
            url: {{url}}
            enum: {{enum}}
            asset: {{asset}}
            texts:{{for(texts)}}
             - {{texts}}{{endfor}}
            urls:{{for(urls)}}
             - {{urls}}{{endfor}}
            enums:{{for(enums)}}
             - {{enums}}{{endfor}}
            assets:{{for(assets)}}
             - {{assets}}{{endfor}}
            """
        })
        all_type.save()
        t1 = Text(text="Foo")
        t1.save()
        t2 = Text(text="Bar")
        t2.save()
        l1 = UriElement(uri="http://ct.de/a")
        l1.save()
        l2 = UriElement(uri="http://ct.de/b")
        l2.save()
        e1 = Enum(t=EnumType.objects.get(pk=2), item="python")
        e1.save()
        e2 = Enum(t=EnumType.objects.get(pk=2), item="c")
        e2.save()
        e3 = Enum(t=EnumType.objects.get(pk=2), item="d")
        e3.save()
        a1 = Asset(t=AssetType.objects.get(type_name="span-regular"), content_ids={"text": t2.pk})
        a1.save()
        a2 = Asset(t=AssetType.objects.get(type_name="span-emphasized"), content_ids={"text": t1.pk})
        a2.save()
        asset = Asset(t=all_type, content_ids={
            "text": t1.pk,
            "url": l1.pk,
            "enum": e1.pk,
            "asset": str(a1.pk),
            "texts": [t1.pk, t2.pk],
            "urls": [l1.pk, l2.pk],
            "enums": [e1.pk, e2.pk, e3.pk],
            "assets": [str(a1.pk), str(a2.pk)]
        })
        asset.save()
        self.maxDiff = None
        self.assertJSONEqual(json.dumps(asset.content), json.dumps({
            "id": str(asset.pk),
            "type": "all_type",
            "text": "Foo",
            "url": "http://ct.de/a",
            "enum": "python",
            "asset": {"id": str(a1.pk), "type": "span-regular", "text": "Bar"},
            "texts": ["Foo", "Bar"],
            "urls": ["http://ct.de/a", "http://ct.de/b"],
            "enums": ["python", "c", "d"],
            "assets": [
                {"id": str(a1.pk), "type": "span-regular", "text": "Bar"},
                {"id": str(a2.pk), "type": "span-emphasized", "text": "Foo"}]
        }))
        self.assertIsNone(asset.raw_content_cache)
        self.assertEqual(asset.render_template(), """
            text: Foo
            url: http://ct.de/a
            enum: python
            asset: Bar
            texts:
             - Foo
             - Bar
            urls:
             - http://ct.de/a
             - http://ct.de/b
            enums:
             - python
             - c
             - d
            assets:
             - Bar
             - Foo
            """)
        self.assertIsNotNone(asset.raw_content_cache)
        self.assertEqual(asset.render_template(), """
            text: Foo
            url: http://ct.de/a
            enum: python
            asset: Bar
            texts:
             - Foo
             - Bar
            urls:
             - http://ct.de/a
             - http://ct.de/b
            enums:
             - python
             - c
             - d
            assets:
             - Bar
             - Foo
            """)

    def test_block_paragraph_raw_template(self):
        t1 = Text(text="Foo ")
        t1.save()
        t2 = Text(text="Bar")
        t2.save()
        a1 = Asset(t=AssetType.objects.get(type_name="span-regular"), content_ids={"text": t1.pk})
        a1.save()
        a2 = Asset(t=AssetType.objects.get(type_name="span-emphasized"), content_ids={"text": t2.pk})
        a2.save()
        p = Asset(t=AssetType.objects.get(type_name="block-paragraph"), content_ids={
            "spans": [str(a1.pk), str(a2.pk)]
        })
        p.save()
        self.assertEqual(p.render_template(), "Foo Bar\n\n")

    def test_block_image_raw_template(self):
        img_uri = UriElement(uri="/foo/bar.jpg")
        img_uri.save()
        alt_text = Text(text="An image of a bar.")
        alt_text.save()
        caption_text1 = Text(text="This bar is an ")
        caption_text1.save()
        caption_text2 = Text(text="example")
        caption_text2.save()
        caption_text3 = Text(text=" of foo.")
        caption_text3.save()
        caption_span1 = Asset(t=AssetType.objects.get(type_name="caption-span-regular"),
                              content_ids={"text": caption_text1.pk})
        caption_span1.save()
        caption_span2 = Asset(t=AssetType.objects.get(type_name="caption-span-emphasized"),
                              content_ids={"text": caption_text2.pk})
        caption_span2.save()
        caption_span3 = Asset(t=AssetType.objects.get(type_name="caption-span-regular"),
                              content_ids={"text": caption_text3.pk})
        caption_span3.save()
        img = Asset(t=AssetType.objects.get(type_name="block-image"), content_ids={
            "image_uri": img_uri.pk,
            "alt": alt_text.pk,
            "caption": [str(caption_span1.pk), str(caption_span2.pk), str(caption_span3.pk)]
        })
        img.save()
        self.assertEqual(img.render_template(),
                         "img (/foo/bar.jpg): An image of a bar.\n\nThis bar is an example of foo.\n")

    def test_block_info_box_raw_template(self):
        t1 = Text(text="Foo ")
        t1.save()
        t2 = Text(text="Bar")
        t2.save()
        s1 = Asset(t=AssetType.objects.get(type_name="span-regular"), content_ids={"text": t1.pk})
        s1.save()
        s2 = Asset(t=AssetType.objects.get(type_name="span-emphasized"), content_ids={"text": t2.pk})
        s2.save()
        p1 = Asset(t=AssetType.objects.get(type_name="block-paragraph"),
                   content_ids={"spans": [str(s1.pk), str(s2.pk)]})
        p1.save()
        p2 = Asset(t=AssetType.objects.get(type_name="block-paragraph"), content_ids={"spans": [str(s2.pk)]})
        p2.save()
        box = Asset(t=AssetType.objects.get(type_name="block-info-box"), content_ids={
            "title": t2.pk,
            "content": [str(p1.pk), str(p2.pk)]
        })
        box.save()
        self.assertEqual(box.render_template(), "Bar\n\nFoo Bar\n\nBar\n\n")


class AssetTypeTests(TestCase):
    fixtures = [
        'span_assets.yaml',
        'caption-span_assets.yaml',
        'block_assets.yaml',
        'table.yaml',
        'enum_types.yaml'
    ]

    def test_str(self):
        span_regular = AssetType.objects.get(type_name="span-regular")
        self.assertEqual(str(span_regular), "<AssetType 6: span-regular !>")
