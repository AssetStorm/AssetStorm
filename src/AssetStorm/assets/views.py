from django.shortcuts import render
from django.db import connection
from django.db.utils import OperationalError
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from AssetStorm.assets.models import AssetType, EnumType, Text, UriElement, Enum, Asset
import json
import yaml
import uuid
import os


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
        elif type(expected_type) is dict and \
                len(expected_type.keys()) == 1 and \
                "3" in expected_type.keys():
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
                    " Assets are saved as JSON-objects with an inner structure matching the schema " +
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
                elif type(asset_type.schema[key]) is int and \
                        asset_type.schema[key] >= 4:
                    check_type(asset_type.schema[key],
                               type(tree[key]),
                               asset_type.type_name,
                               key,
                               tree[key])
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
        except EnumType.DoesNotExist:
            raise AssetStructureError(tree, "Unknown EnumType: %s." % str(tree[key]))
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
        asset.content_cache = None
        asset.clear_reference_lists()
        asset.save()
        changed = False
        for key in asset.t.schema.keys():
            if key in tree:
                if asset.t.schema[key] == 1:
                    old_text = Text.objects.get(pk=asset.content_ids[key])
                    if tree[key] != old_text.text:
                        changed = True
                        asset.content_ids[key] = create_asset(tree[key], item_type=asset.t.schema[key])
                elif asset.t.schema[key] == 2:
                    old_uri = UriElement.objects.get(pk=asset.content_ids[key])
                    if tree[key] != old_uri.uri:
                        changed = True
                        asset.content_ids[key] = create_asset(tree[key], item_type=asset.t.schema[key])
                elif type(asset.t.schema[key]) is dict and \
                        len(asset.t.schema[key].keys()) == 1 and \
                        "3" in asset.t.schema[key].keys():
                    old_enum = Enum.objects.get(pk=asset.content_ids[key])
                    if tree[key] != old_enum.item:
                        changed = True
                        asset.content_ids[key] = create_asset(tree[key], item_type=asset.t.schema[key])
                elif type(asset.t.schema[key]) is list:
                    item_ids_list = []
                    for list_item in tree[key]:
                        item_ids_list.append(create_or_modify_asset(list_item, item_type=asset.t.schema[key][0]))
                    for i, new_item in enumerate(item_ids_list):
                        if old_asset.content_ids[key][i] != new_item:
                            changed = True
                    asset.content_ids[key] = item_ids_list
                else:
                    asset.content_ids[key] = create_or_modify_asset(tree[key], item_type=asset.t.schema[key])
                    if asset.content_ids[key] != old_asset.content_ids[key]:
                        changed = True
        if changed:
            asset.clear_cache()
        else:
            asset.revision_chain = old_asset.revision_chain
            asset.save()
            old_asset.delete()
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
            "success": True,
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


def turnout(request):
    if request.method == 'GET':
        return load_asset(request)
    if request.method == 'POST':
        return save_asset(request)


def query(request, query_string=""):
    if request.content_type != "application/json" and len(request.body) > 0:
        return HttpResponseBadRequest(content=json.dumps({
            "Error": "If you supply filters they need to be valid JSON and " +
                     "the request must have the MIME-type \"application/json\"."
        }), content_type="application/json")
    try:
        if request.body is not None and len(request.body) > 0 and request.content_type == "application/json":
            json_filters = json.loads(request.body, encoding='utf-8')
        else:
            json_filters = {}
        found_assets = Asset.objects.filter(
            new_version=None).filter(
            raw_content_cache__icontains=query_string).filter(
            content_cache__contains=json_filters)
        return HttpResponse(content=json.dumps({
            "assets": [{
                "id": str(a.pk),
                "type_id": a.t.pk,
                "raw_content_snippet": a.raw_content_cache[:500]
            } for a in found_assets]
        }), content_type="application/json")
    except json.decoder.JSONDecodeError:
        return HttpResponseBadRequest(content=json.dumps({
            "Error": "The filters are not in JSON format. The request body has to be valid JSON."
        }), content_type="application/json")


def get_template(request):
    if "type_name" not in request.GET or "template_type" not in request.GET:
        return HttpResponseBadRequest(content=json.dumps({
            "Error": "You must supply template_type and type_name as GET params."
        }), content_type="application/json")
    try:
        ato = AssetType.objects.get(type_name=request.GET["type_name"])
    except AssetType.DoesNotExist:
        return HttpResponseBadRequest(content=json.dumps({
            "Error": "The AssetType \"" + request.GET["type_name"] + "\" does not exist."
        }), content_type="application/json")
    if request.GET["template_type"] not in ato.templates.keys():
        return HttpResponseBadRequest(content=json.dumps({
            "Error": "The AssetType \"" + request.GET["type_name"] +
                     "\" has no template \"" + request.GET["template_type"] + "\"."
        }), content_type="application/json")
    return HttpResponse(content=ato.templates[request.GET["template_type"]],
                        content_type="text/plain")


def get_schema(request):
    if "type_name" not in request.GET and "type_id" not in request.GET:
        return JsonResponse(data={
            "Error": "You must supply a type_name or a type_id as GET params."
        }, status=400)
    try:
        if "type_id" in request.GET:
            ato = AssetType.objects.get(pk=int(request.GET["type_id"]))
        else:
            ato = AssetType.objects.get(type_name=request.GET["type_name"])
    except AssetType.DoesNotExist:
        return JsonResponse(data={
            "Error": "The AssetType \"" + request.GET["type_name"] + "\" does not exist."
        }, status=400)
    if ato.schema is None:
        return JsonResponse(data={})
    return JsonResponse(data=ato.schema)


def get_types_for_parent(request):
    if "parent_type_name" not in request.GET:
        return HttpResponseBadRequest(content=json.dumps({
            "Error": "You must supply parent_type_name as GET param."
        }), content_type="application/json")
    try:
        parent = AssetType.objects.get(type_name=request.GET["parent_type_name"])
    except AssetType.DoesNotExist:
        return HttpResponseBadRequest(content=json.dumps({
            "Error": "The AssetType \"" + request.GET["parent_type_name"] + "\" does not exist."
        }), content_type="application/json")
    children = [child.type_name for child in parent.children.all()]
    return HttpResponse(content=json.dumps(children),
                        content_type="application/json")


def deliver_open_api_definition(request):
    with open("AssetStormAPI.yaml", 'r') as yaml_file:
        api_definition = yaml.safe_load(yaml_file.read())
    if os.getenv("SERVER_NAME") is not None:
        api_definition["servers"][0]['url'] = os.getenv("SERVER_NAME")
    return HttpResponse(content=json.dumps(api_definition),
                        content_type="application/json")


def live(request):
    try:
        connection.ensure_connection()
        return HttpResponse(content="", content_type="text/plain", status=200)
    except OperationalError:
        return HttpResponse(content="", content_type="text/plain", status=400)
