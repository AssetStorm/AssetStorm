from django.shortcuts import render
from django.http import HttpResponseBadRequest, HttpResponse
from assets.models import AssetType, EnumType, Text, UriElement, Enum, Asset
import json
import uuid


class AssetStructureError(Exception):
    def __init__(self, asset=None, *args):
        super(Exception, self).__init__(*args)
        self.asset = asset


def load_asset(request):
    if "id" not in request.GET:
        return HttpResponseBadRequest(content=json.dumps({
            "Error": "Please supply a 'id' as a GET param."
        }), content_type="application/json")
    try:
        asset = Asset.objects.get(pk=request.GET["id"])
        return HttpResponse(content=json.dumps(asset.content),
                            content_type="application/json")
    except Asset.DoesNotExist:
        return HttpResponseBadRequest(content=json.dumps({
            "Error": "No Asset with id=%s found." % request.GET["id"]
        }), content_type="application/json")


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
            if "id" in tree.keys():
                try:
                    uuid.UUID(tree["id"], version=4)
                except ValueError:
                    raise AssetStructureError(tree, "The id '%s' is not a valid uuid (v4)." % tree["id"])
                Asset.objects.get(pk=tree["id"])
                if "type" not in tree.keys():
                    return None
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
        except Asset.DoesNotExist:
            raise AssetStructureError(tree, "An Asset with id %s does not exist." % tree["id"])

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
                    item_ids_list.append(create_or_modify_asset(list_item, item_type=asset_type.schema[key][0]))
                content_ids[key] = item_ids_list
            else:
                content_ids[key] = create_or_modify_asset(tree[key], item_type=asset_type.schema[key])
        asset = Asset(t=asset_type, content_ids=content_ids)
        asset.save()
        return str(asset.pk)

    def modify_asset(tree):
        old_asset = Asset.objects.get(pk=tree["id"])
        old_asset.pk = None
        old_asset.save()
        asset = Asset.objects.get(pk=tree["id"])
        asset.revision_chain = old_asset
        for key in asset.t.schema.keys():
            if key in tree:
                if asset.t.schema[key] == 1:
                    old_text = Text.objects.get(pk=asset.content_ids[key])
                    if tree[key] != old_text.text:
                        asset.content_ids[key] = create_asset(tree[key], item_type=asset.t.schema[key])
                elif asset.t.schema[key] == 2:
                    old_uri = UriElement.objects.get(pk=asset.content_ids[key])
                    if tree[key] != old_uri.uri:
                        asset.content_ids[key] = create_asset(tree[key], item_type=asset.t.schema[key])
                elif type(asset.t.schema[key]) is dict and \
                        len(asset.t.schema[key].keys()) == 1 and \
                        "3" in asset.t.schema[key].keys():
                    old_enum = Enum.objects.get(pk=asset.content_ids[key])
                    if tree[key] != old_enum.item:
                        asset.content_ids[key] = create_asset(tree[key], item_type=asset.t.schema[key])
                elif type(asset.t.schema[key]) is list:
                    item_ids_list = []
                    for list_item in tree[key]:
                        item_ids_list.append(create_or_modify_asset(list_item, item_type=asset.t.schema[key][0]))
                    asset.content_ids[key] = item_ids_list
                else:
                    asset.content_ids[key] = create_or_modify_asset(tree[key], item_type=asset.t.schema[key])
        asset.save()
        return str(asset.pk)

    def create_or_modify_asset(tree, item_type=None):
        if type(tree) is dict and "id" in tree.keys():
            return modify_asset(tree)
        return create_asset(tree, item_type)

    try:
        full_tree = json.loads(request.body, encoding='utf-8')
        check_asset(full_tree)
        asset_pk = create_or_modify_asset(full_tree)
        return HttpResponse(content=json.dumps({
            "Success": True,
            "id": asset_pk
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
