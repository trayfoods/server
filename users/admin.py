from django.conf import settings
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
    UserDevice,
    HostelField,
)
from .forms import HostelForm, StudentForm

STATIC_URL = settings.STATIC_URL

ROLE_CHOICES = (
    ("VENDOR", "VENDOR"),
    ("CLIENT", "CLIENT"),
    ("DELIVERY_PERSON", "DELIVERY_PERSON"),
    ("STUDENT", "STUDENT"),
)


class RolesFilter(admin.SimpleListFilter):
    title = "Roles"
    parameter_name = "roles"

    def lookups(self, request, model_admin):
        return ROLE_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            users = UserAccount.objects.all()
            list_of_users = []
            for user in users:
                if self.value() in user.roles:
                    list_of_users.append(user.id)
            return queryset.filter(id__in=list_of_users)


class ProfileInline(admin.TabularInline):
    model = Profile
    extra = 0
    readonly_fields = (
        "gender",
        "country",
        "address",
        "school",
        "hostel",
        "phone_number",
    )


class UserAccountAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "username", "roles")
    search_fields = ("username", "first_name", "last_name", "email")
    list_filter = (RolesFilter,)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(is_staff=True)


class StoreInline(admin.TabularInline):
    model = Store
    extra = 0
    readonly_fields = ("store_name", "store_country", "store_address", "school")


class UserInline(admin.TabularInline):
    model = UserAccount
    extra = 0
    readonly_fields = ("email", "first_name", "last_name", "username", "roles")


class ProfileAdmin(admin.ModelAdmin):
    inlines = [StoreInline]
    list_filter = (RolesFilter,)
    readonly_fields = ("user",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(user__is_staff=True)


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


class HostelFieldInline(admin.TabularInline):
    model = HostelField
    extra = 0


class SchoolAdmin(admin.ModelAdmin):
    inlines = [HostelFieldInline]
    list_display = ("name", "country", "date_created")
    search_fields = ("name", "country")
    list_filter = ("country",)
    readonly_fields = ("slug", "date_created")


class HostelAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "gender")
    search_fields = ("name", "school__name")
    list_filter = ("school", "gender")
    readonly_fields = ("slug", "date_created")
    form = HostelForm

    class Media:
        js = (f"{STATIC_URL}js/custom-admin.js",)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "fields":
            # get the hostel school
            hostel_id = request.resolver_match.kwargs.get("object_id")
            if not hostel_id:
                kwargs["queryset"] = HostelField.objects.none()
                return super().formfield_for_manytomany(db_field, request, **kwargs)
            hostel = Hostel.objects.get(id=hostel_id)
            # get the school fields
            fields = hostel.school.hostel_fields.all()
            # set the fields
            kwargs["queryset"] = fields
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class TransactionAdmin(admin.ModelAdmin):
    list_display = ("wallet", "amount", "status", "_type", "created_at")
    search_fields = (
        "wallet__user__user__username",
        "wallet__user__user__email",
        "transaction_id",
        "gateway_transfer_id",
    )
    list_filter = ("created_at", "_type")
    readonly_fields = (
        "wallet",
        "amount",
        "transaction_id",
        "gateway_transfer_id",
        "_type",
        "created_at",
    )


class DeliveryPersonAdmin(admin.ModelAdmin):
    list_display = ("__str__", "is_on_delivery", "is_verified", "is_available")


class StudentAdmin(admin.ModelAdmin):
    list_display = ("__str__", "school", "campus", "hostel")
    search_fields = ("user__user__username", "user__user__email")
    list_filter = ("school", "campus", "hostel")
    readonly_fields = ("user",)
    form = StudentForm

    class Media:
        js = (f"{STATIC_URL}js/custom-admin.js",)


admin.site.register(Gender)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Store)
admin.site.register(Student, StudentAdmin)
admin.site.register(Hostel, HostelAdmin)
admin.site.register(DeliveryPerson, DeliveryPersonAdmin)

admin.site.register(UserAccount, UserAccountAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(School, SchoolAdmin)
admin.site.register(UserDevice)
admin.site.register(Transaction, TransactionAdmin)
