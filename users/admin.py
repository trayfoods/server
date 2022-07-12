from django.contrib import admin
from users.models import Client, Vendor, Store, Profile, Hostel, Gender


admin.site.register(Gender)
admin.site.register(Profile)
admin.site.register(Store)
admin.site.register(Vendor)
admin.site.register(Client)
admin.site.register(Hostel)
