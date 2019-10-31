# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from assets.models import Asset


class Command(BaseCommand):
    help = "Build the content and raw_template cache for all Asset which do not have one"

    def handle(self, *args, **options):
        print("Building all missing caches...")
        for asset in Asset.objects.filter(content_cache__isnull=True):
            print("asset without content:", asset)
            _ = asset.content
        for asset in Asset.objects.filter(raw_content_cache__isnull=True):
            print("asset without raw_content:", asset)
            _ = asset.render_template("raw")
