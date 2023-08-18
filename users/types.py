import json

from profile import Profile
import graphene
from graphene_django.types import DjangoObjectType
from graphql_auth.schema import UserNode
from .models import (
    UserAccount,
    School,
    Client,
    Vendor,
    Store,
    Profile,
    Hostel,
    Gender,
    Transaction,
)


class SchoolType(DjangoObjectType):
    class Meta:
        model = School
        fields = "__all__"


class ProfileType(DjangoObjectType):
    class Meta:
        model = Profile
        fields = "__all__"

    def resolve_image(self, info, *args, **kwargs):
        if self.image:
            image = info.context.build_absolute_uri(self.image.url)
        else:
            image = None
        return image


class UserNodeType(UserNode, graphene.ObjectType):
    profile = graphene.Field(ProfileType)

    class Meta:
        model = UserAccount
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "role",
            "profile",
        ]

    def resolve_role(self, info):
        role = self.role
        # confirm if role is the correct role
        user = UserAccount.objects.filter(id=self.id).first()
        profile = Profile.objects.filter(user=user).first()
        vendor = Vendor.objects.filter(user=profile).first()
        client = Client.objects.filter(user=profile).first()
        if not vendor is None:
            role = "vendor"

        if not client is None:
            role = "student"

        if client is None and vendor is None:
            role = "client"
        return role.lower()

    def resolve_profile(self, info):
        return self.profile


class GenderType(DjangoObjectType):
    class Meta:
        model = Gender
        fields = "__all__"


class HostelType(DjangoObjectType):
    class Meta:
        model = Hostel
        fields = "__all__"


class ClientType(DjangoObjectType):
    class Meta:
        model = Client
        fields = "__all__"


class TransactionType(DjangoObjectType):
    class Meta:
        model = Transaction
        fields = ["id", "title", "amount", "desc", "created_at", "_type"]


class VendorType(DjangoObjectType):
    profile = graphene.Field(ProfileType)

    class Meta:
        model = Vendor
        fields = [
            "id",
            "profile",
            "store",
            "account_number",
            "account_name",
            "bank_code",
            "created_at",
        ]

    def resolve_id(self, info):
        return self.pk

    def resolve_profile(self, info):
        # user = Profile.objects.filter(user=).first()
        return self.user.user.profile


class StoreType(DjangoObjectType):
    store_country = graphene.String()
    store_categories = graphene.List(graphene.String)
    store_phone_numbers = graphene.List(graphene.String)
    store_image = graphene.String()
    store_cover_image = graphene.String()
    store_products = graphene.List("product.schema.ItemType")

    class Meta:
        model = Store
        fields = [
            "vendor",
            "store_name",
            "store_country",
            "store_type",
            "store_categories",
            "store_phone_numbers",
            "store_bio",
            "store_address",
            "store_nickname",
            "store_school",
            "store_image",
            "store_cover_image",
            "store_products",
            "store_rank",
        ]

    def resolve_store_country(self, info):
        return self.store_country.name

    def resolve_store_categories(self, info):
        return self.store_categories

    def resolve_store_phone_numbers(self, info):
        return self.store_phone_numbers

    def resolve_store_products(self, info):
        return self.store_products.all()

    def resolve_store_image(self, info):
        store = Store.objects.filter(vendor=self.vendor).first()
        vendor = store.vendor
        if vendor is None:
            return None
        profile = vendor.user
        image = None
        try:
            image = info.context.build_absolute_uri(profile.image.url)
        except:
            pass
        return image

    def resolve_cover_store_image(self, info):
        return info.context.build_absolute_uri(self.store_cover_image.url)
