from django.contrib import admin
from users.models import Client, Vendor, Store, Profile


admin.site.register(Profile)
admin.site.register(Store)
admin.site.register(Vendor)
admin.site.register(Client)
