from django.contrib import admin
from users.models import Client, Vendor, Store, Profile, Hostel, Gender


class VendorAdmin(admin.ModelAdmin):
    list_display = ('user', 'store', 'account_number',
                    'account_name', 'created_at')
    search_fields = ('user__user__username', 'bank_code',
                     'store__store_name', 'account_number', 'account_name')
    list_filter = ('created_at',)


admin.site.register(Gender)
admin.site.register(Profile)
admin.site.register(Store)
admin.site.register(Vendor, VendorAdmin)
admin.site.register(Client)
admin.site.register(Hostel)
