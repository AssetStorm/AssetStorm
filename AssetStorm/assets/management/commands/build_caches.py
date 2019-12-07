# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from AssetStorm.assets.models import Asset


class Command(BaseCommand):
    help = "Build the content and raw_template cache for all Asset which do not have one"

    def handle(self, *args, **options):
        for asset in Asset.objects.filter(content_cache__isnull=True):
            _ = asset.content
        for asset in Asset.objects.filter(raw_content_cache__isnull=True):
            _ = asset.render_template("raw")
