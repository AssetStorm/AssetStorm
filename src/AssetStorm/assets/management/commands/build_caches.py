# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from AssetStorm.assets.views import update_caches
import json


class Command(BaseCommand):
    help = "Build the content and raw_template cache for all Asset which do not have one"

    def handle(self, *args, **options):
        response = update_caches()
        print("rebuilt_content_caches:",
              json.loads(str(response.content, encoding="utf-8"))['rebuilt_content_caches'])
        print("rendered_raw_templates:",
              json.loads(str(response.content, encoding="utf-8"))['rendered_raw_templates'])
