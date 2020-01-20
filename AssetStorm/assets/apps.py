from django.apps import AppConfig


class AssetConfig(AppConfig):
    """
    App config. See https://docs.djangoproject.com/en/3.0/ref/applications/#for-application-authors
    """
    name = 'AssetStorm.assets'
    verbose_name = "Base app for AssetStorm which hosts the models and basic views."
