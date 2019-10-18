#!/usr/bin/python3
# -*- coding: utf-8 -*-
from .models import AssetType, Asset, Text, UriElement, Enum
import pypandoc
import json


def consume_str(content_list):
    consumed_text = ""
    for i, span in enumerate(content_list):
        if span['t'] == "Space":
            consumed_text += " "
        elif span['t'] == "Str":
            consumed_text += span['c']
        else:
            return consumed_text, content_list[i:]
    return consumed_text, []


def create_span_assets(spans):
    block_ids = []
    if spans[0]['t'] == "Strong":
        span_type = AssetType.objects.get(type_name='span-strong')
        block_ids = spans[0]['c']
    elif spans[0]['t'] == "Emph":
        span_type = AssetType.objects.get(type_name='span-emphasized')
    elif spans[0]['t'] == "Code":
        span_type = AssetType.objects.get(type_name='span-listing')


def create_assets_from_markdown(markdown):
    block_assets_list = []
    pandoc_tree = json.loads(pypandoc.convert_text(markdown, to='json', format='md'))
    print(json.dumps(pandoc_tree, indent=2))
    for block in pandoc_tree['blocks']:
        if block['t'] == 'Para':
            block_ids = []
            block_spans = block['c'].copy()
            while len(block_spans) > 0:
                span_type = AssetType.objects.get(type_name='span-regular')
                if block_spans[0]['t'] == "Strong":
                    span_type = AssetType.objects.get(type_name='span-strong')
                elif block_spans[0]['t'] == "Emph":
                    span_type = AssetType.objects.get(type_name='span-emphasized')
                elif block_spans[0]['t'] == "Code":
                    span_type = AssetType.objects.get(type_name='span-listing')
                old_block_spans_len = len(block_spans)
                text, block_spans = consume_str(block_spans)
                if not len(block_spans) < old_block_spans_len:
                    print("Consumation error!")
                    print(block_spans)
                    break
                text_obj = Text(text=text)
                text_obj.save()
                id_key = 'listing_text' if span_type.type_name == 'span-listing' else 'text'
                asset_obj = Asset(t=span_type, content_ids={id_key: text_obj.pk})
                asset_obj.save()
                block_ids.append(str(asset_obj.pk))
            paragraph_asset = Asset(t=AssetType.objects.get(type_name='block-paragraph'),
                                    content_ids={'spans': block_ids})
            paragraph_asset.save()
            block_assets_list.append(paragraph_asset)
    return block_assets_list

