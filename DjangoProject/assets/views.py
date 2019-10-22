from django.shortcuts import render
from django.http import HttpResponseBadRequest, HttpResponse
from assets.models import AssetType, EnumType, Text, UriElement, Enum, Asset
import json


class AssetStructureError(Exception):
    def __init__(self, asset=None, *args):
        super(Exception, self).__init__(*args)
        self.asset = asset


def save_asset(request):
    def check_type(expected_type, actual_type, asset_type_name, current_key, current_tree):
        if expected_type == 1:
            if actual_type is not str:
                raise AssetStructureError(
                    current_tree,
                    "The Schema of AssetType '%s' demands the content for key '%s' to be a string." % (
                        asset_type_name,
                        current_key))
        elif expected_type == 2:
            if actual_type is not str:
                raise AssetStructureError(
                    current_tree,
                    "The Schema of AssetType '%s' demands the content for key '%s' to be a string with a URI." % (
                        asset_type_name,
                        current_key))
        elif type(expected_type) is dict and len(expected_type.keys()) == 1:
            enum_type = EnumType.objects.get(pk=expected_type["3"])
            if current_tree[current_key] not in enum_type.items:
                raise AssetStructureError(
                    current_tree,
                    "The Schema of AssetType '%s' demands the content for key '%s' to be the enum_type with id=%d." % (
                        asset_type_name,
                        current_key,
                        enum_type.pk))
        else:
            if actual_type is dict:
                check_asset(current_tree, expected_asset_type_id=expected_type)
            else:
                raise AssetStructureError(
                    current_tree,
                    "The Schema of AssetType '%s' demands the content for key '%s' to be an Asset." % (
                        asset_type_name,
                        current_key) +
                    "Assets are saved as JSON-objects with an inner structure matching the schema " +
                    "of their type.")

    def check_asset(tree, expected_asset_type_id=None):
        try:
            asset_type = AssetType.objects.get(type_name=tree["type"])
            if expected_asset_type_id is not None and (
                    asset_type.pk != expected_asset_type_id and
                    asset_type.parent_type.pk != expected_asset_type_id):
                raise AssetStructureError(
                    tree,
                    "Expected an AssetType with id %d but got '%s' with id %d." % (
                        expected_asset_type_id,
                        asset_type.type_name,
                        asset_type.pk))
            for key in asset_type.schema.keys():
                if key not in tree:
                    raise AssetStructureError(
                        tree,
                        "Missing key '%s' in AssetType '%s'." % (
                            key,
                            asset_type.type_name))
                if type(asset_type.schema[key]) is list:
                    if type(tree[key]) is not list:
                        raise AssetStructureError(
                            tree,
                            "The Schema of AssetType '%s' demands the content for key '%s' to be a List." % (
                                asset_type.type_name,
                                key))
                    for list_item in tree[key]:
                        check_type(asset_type.schema[key][0],
                                   type(list_item),
                                   asset_type.type_name,
                                   key,
                                   list_item)
                else:
                    check_type(asset_type.schema[key],
                               type(tree[key]),
                               asset_type.type_name,
                               key,
                               tree)
        except KeyError as err:
            raise AssetStructureError(tree, "Missing key in Asset: " + str(err))
        except AssetType.DoesNotExist:
            raise AssetStructureError(tree, "Unknown AssetType: " + tree["type"])
        except Enum.DoesNotExist:
            raise AssetStructureError(tree, "Unknown Enum: " + str(tree[key]))

    def create_asset(tree, item_type=None):
        if item_type == 1:
            text_item = Text(text=tree)
            text_item.save()
            return text_item.pk
        if item_type == 2:
            uri_item = UriElement(uri=tree)
            uri_item.save()
            return uri_item.pk
        if type(item_type) is dict and \
                len(item_type.keys()) == 1 and \
                "3" in item_type.keys():
            enum_item = Enum(t=EnumType.objects.get(pk=item_type["3"]), item=tree)
            enum_item.save()
            return enum_item.pk
        asset_type = AssetType.objects.get(type_name=tree["type"])
        content_ids = {}
        for key in asset_type.schema.keys():
            if type(asset_type.schema[key]) is list:
                item_ids_list = []
                for list_item in tree[key]:
                    item_ids_list.append(create_asset(list_item, item_type=asset_type.schema[key][0]))
                content_ids[key] = item_ids_list
            else:
                content_ids[key] = create_asset(tree[key], item_type=asset_type.schema[key])
        asset = Asset(t=asset_type, content_ids=content_ids)
        asset.save()
        return str(asset.pk)

    try:
        full_tree = json.loads(request.body, encoding='utf-8')
        check_asset(full_tree)
        create_asset(full_tree)
        return HttpResponse(content=json.dumps({
            "Success": True
        }), content_type="application/json")
    except json.decoder.JSONDecodeError:
        return HttpResponseBadRequest(content=json.dumps({
            "Error": "Request not in JSON format. The requests body has to be valid JSON."
        }), content_type="application/json")
    except AssetStructureError as asset_error:
        return HttpResponseBadRequest(content=json.dumps({
            "Error": str(asset_error),
            "Asset": asset_error.asset
        }), content_type="application/json")
