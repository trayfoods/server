from django.conf import settings
from storages.backends.azure_storage import AzureStorage
import re


class AzureMediaStorage(AzureStorage):
    account_name = settings.AZURE_ACCOUNT_NAME
    account_key = settings.AZURE_ACCOUNT_KEY
    azure_container = "media"
    expiration_secs = None

    def url(self, name):
        blob_url = super(AzureMediaStorage, self).url(name)
        imagekit_url = re.sub(
            r"https://[a-z.0-9A-Z]*", settings.MEDIA_URL, blob_url
        )
        return imagekit_url


class AzureStaticStorage(AzureStorage):
    account_name = settings.AZURE_ACCOUNT_NAME
    account_key = settings.AZURE_ACCOUNT_KEY
    azure_container = "static"
    expiration_secs = None
