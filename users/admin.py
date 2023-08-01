from django.contrib import admin
from users.models import (
    Client,
    Vendor,
    Store,
    Profile,
    Hostel,
    Gender,
    UserAccount,
    DeliveryPerson,
    Wallet,
    School,
    Country,
    Transaction,
)


class UserAccountAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "username", "role")
    search_fields = ("username", "role", "first_name", "last_name", "email")
    list_filter = ("id",)


class VendorAdmin(admin.ModelAdmin):
    list_display = ("user", "store", "account_number", "account_name", "created_at")
    search_fields = (
        "user__user__username",
        "bank_code",
        "store__store_name",
        "account_number",
        "account_name",
    )
    list_filter = ("created_at",)


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ("wallet", "amount", "_type", "created_at")


class WalletAdmin(admin.ModelAdmin):
    inlines = [TransactionInline]
    list_display = ("user", "currency", "balance", "created_at", "updated_at")
    search_fields = ("user__user__username", "currency", "user__user__email")
    list_filter = ("created_at", "updated_at", "currency")
    readonly_fields = (
        "user",
        "balance",
        "currency",
        "uncleared_balance",
        "created_at",
        "updated_at",
    )

class TransactionAdmin(admin.ModelAdmin):
    list_display = ("wallet", "amount", "_type", "created_at")
    search_fields = ("wallet__user__user__username", "wallet__user__user__email")
    list_filter = ("created_at", "_type")
    readonly_fields = ("wallet", "amount", "_type", "created_at")

admin.site.register(Gender)
admin.site.register(Profile)
admin.site.register(Store)
admin.site.register(Client)
admin.site.register(Hostel)
admin.site.register(DeliveryPerson)

admin.site.register(UserAccount, UserAccountAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(Vendor, VendorAdmin)
admin.site.register(School)
admin.site.register(Country)
admin.site.register(Transaction, TransactionAdmin)
