from django.contrib import admin
from users.models import (
    Student,
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


class RoleFilter(admin.SimpleListFilter):
    title = "Role"
    parameter_name = "role"

    def lookups(self, request, model_admin):
        return ROLE_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            users = UserAccount.objects.all()
            list_of_users = []
            for user in users:
                if user.role == self.value():
                    list_of_users.append(user.id)
            return queryset.filter(id__in=list_of_users)
        else:
            return queryset

class ProfileInline(admin.TabularInline):
    model = Profile
    extra = 0
    readonly_fields = ("gender", "country", "address", "school", "hostel", "phone_number")

class UserAccountAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "username", "role")
    search_fields = ("username", "first_name", "last_name", "email")
    list_filter = (RoleFilter,)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(is_staff=True)


class StoreInline(admin.TabularInline):
    model = Store
    extra = 0
    readonly_fields = ("store_name", "store_country", "store_address", "store_school")

class UserInline(admin.TabularInline):
    model = UserAccount
    extra = 0
    readonly_fields = ("email", "first_name", "last_name", "username", "role")


class ProfileAdmin(admin.ModelAdmin):
    inlines = [StoreInline]
    list_filter = (RoleFilter,)


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ("wallet", "amount", "transaction_id", "_type", "created_at")


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
    list_display = ("wallet", "amount", "status", "_type", "created_at")
    search_fields = ("wallet__user__user__username", "wallet__user__user__email", "transaction_id", "gateway_transfer_id")
    list_filter = ("created_at", "_type")
    readonly_fields = ("wallet", "amount", "transaction_id", "gateway_transfer_id", "_type", "created_at")


admin.site.register(Gender)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Store)
admin.site.register(Student)
admin.site.register(Hostel)
admin.site.register(DeliveryPerson)

admin.site.register(UserAccount, UserAccountAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(School)
admin.site.register(Transaction, TransactionAdmin)
