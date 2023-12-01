from django.conf import settings
from storages.backends.azure_storage import AzureStorage
import re


class AzureMediaStorage(AzureStorage):
    account_name = settings.AZURE_ACCOUNT_NAME
    account_key = settings.AZURE_ACCOUNT_KEY
    azure_container = "media"
    expiration_secs = None

    def url(self, name):
        ret = super(AzureMediaStorage, self).url(name)
        _ret = re.sub("//[a-z.0-9A-Z]*/", settings.MEDIA_URL, ret)
        return _ret


class AzureStaticStorage(AzureStorage):
    account_name = settings.AZURE_ACCOUNT_NAME
    account_key = settings.AZURE_ACCOUNT_KEY
    azure_container = "static"
    expiration_secs = None
