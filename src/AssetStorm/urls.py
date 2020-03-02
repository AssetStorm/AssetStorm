"""AssetStorm URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from AssetStorm.assets.views import load_asset, save_asset, turnout, query
from AssetStorm.assets.views import get_template, get_schema, get_types_for_parent
from AssetStorm.assets.views import deliver_open_api_definition, live, update_caches

urlpatterns = [
    path('', turnout, name="turnout_request"),
    path('load', load_asset, name="load_asset"),
    path('save', save_asset, name="save_asset"),
    path('find', query, {"query_string": ""}, name="filter_assets"),
    path('find/<str:query_string>', query, name="find_assets"),
    path('get_template', get_template, name="get_template"),
    path('get_schema', get_schema, name="get_schema"),
    path('get_types_for_parent', get_types_for_parent, name="get_types_for_parent"),
    path('update_caches', update_caches, name="update_caches"),
    path('openapi.json', deliver_open_api_definition, name="openapi.json"),
    path('live', live, name="live")
]
