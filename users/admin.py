from django.contrib import admin
from users.models import (
    Student,
    Vendor,
    Store,
    Profile,
    Hostel,
    Gender,
    UserAccount,
    DeliveryPerson,
    Wallet,
    School,
    Transaction,
)

ROLE_CHOICES = (
    ("VENDOR", "VENDOR"),
    ("CLIENT", "CLIENT"),
    ("DELIVERY_PERSON", "DELIVERY_PERSON"),
    ("STUDENT", "STUDENT"),
    ("SCHOOL", "SCHOOL"),
)


class UserFilter(admin.SimpleListFilter):
    title = "Role"
    parameter_name = "role"

    def lookups(self, request, model_admin):
        return ROLE_CHOICES

    def queryset(self, request, queryset):
        print(self.value())
        if self.value():
            users = UserAccount.objects.all()
            list_of_users = []
            for user in users:
                if user.role == self.value():
                    list_of_users.append(user.id)
            return queryset.filter(id__in=list_of_users)
        else:
            return queryset


class UserAccountAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "username", "role")
    search_fields = ("username", "first_name", "last_name", "email")
    list_filter = (UserFilter,)


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
admin.site.register(Student)
admin.site.register(Hostel)
admin.site.register(DeliveryPerson)

admin.site.register(UserAccount, UserAccountAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(Vendor, VendorAdmin)
admin.site.register(School)
admin.site.register(Transaction, TransactionAdmin)
