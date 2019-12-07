from django.apps import AppConfig

class AssetConfig(AppConfig):
    """
    Required config, to make this Django application such one.

    See https://docs.djangoproject.com/en/2.2/ref/applications/#for-application-authors
    """
    name = 'AssetStorm.assets'
    verbose_name = "The one for the assets"
