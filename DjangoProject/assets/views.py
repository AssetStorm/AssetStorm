from django.shortcuts import render
from django.http import HttpResponseBadRequest, HttpResponse
from assets.models import AssetType, Enum
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
            enum = Enum.objects.get(pk=expected_type["3"])
            if current_tree[current_key] not in enum.items:
                raise AssetStructureError(
                    current_tree,
                    "The Schema of AssetType '%s' demands the content for key '%s' to be the enum with id=%d." % (
                        asset_type_name,
                        current_key,
                        enum.pk))
        else:
            if actual_type is dict:
                check_asset(current_tree, expected_asset_id=expected_type)
            else:
                raise AssetStructureError(
                    current_tree,
                    "The Schema of AssetType '%s' demands the content for key '%s' to be an Asset." % (
                        asset_type_name,
                        current_key) +
                    "Assets are saved as JSON-objects with an inner structure matching the schema " +
                    "of their type.")

    def check_asset(tree, expected_asset_id=None):
        try:
            asset_type = AssetType.objects.get(type_name=tree["type"])
            if expected_asset_id is not None and (
                    asset_type.pk != expected_asset_id and
                    asset_type.parent_type.pk != expected_asset_id):
                raise AssetStructureError(
                    tree,
                    "Expected an Asset with id %d but got '%s' with id %d." % (
                        expected_asset_id,
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
            return str(asset_type.schema)
        except KeyError as err:
            raise AssetStructureError(tree, "Missing key in Asset: " + str(err))
        except AssetType.DoesNotExist:
            raise AssetStructureError(tree, "Unknown AssetType: " + tree["type"])
        except Enum.DoesNotExist:
            raise AssetStructureError(tree, "Unknown Enum: " + str(tree[key]))

    try:
        full_tree = json.loads(request.body, encoding='utf-8')
        check_result = check_asset(full_tree)
        return HttpResponse(content=json.dumps({
            "Success": True,
            "check_result": check_result
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
