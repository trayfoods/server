import graphene
from graphene_django.types import DjangoObjectType
from graphql_auth.schema import UserNode

from trayapp.utils import convert_time_to_ago

from users.filters import TransactionFilter
from .models import (
    UserAccount,
    School,
    Student,
    Vendor,
    Store,
    Profile,
    Hostel,
    Gender,
    Transaction,
)


class SchoolType(DjangoObjectType):
    campuses = graphene.List(graphene.String)

    class Meta:
        model = School
        fields = "__all__"

    def resolve_campuses(self, info):
        return self.campuses


class ProfileType(DjangoObjectType):
    is_student = graphene.Boolean()

    class Meta:
        model = Profile
        fields = "__all__"

    def resolve_image(self, info, *args, **kwargs):
        if self.image:
            image = info.context.build_absolute_uri(self.image.url)
        else:
            image = None
        return image

    def resolve_is_student(self, info, *args, **kwargs):
        # check if the user role is student
        return self.user.role == "STUDENT"


class UserNodeType(UserNode, graphene.ObjectType):
    profile = graphene.Field(ProfileType)
    orders = graphene.List("product.schema.OrderType")
    role = graphene.String()

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
            "orders",
        ]

    def resolve_role(self, info):
        return self.role

    def resolve_orders(self, info):
        return self.orders.all()

    def resolve_profile(self, info):
        return self.profile


class WalletInfoNode(graphene.ObjectType):
    balance = graphene.String()
    success = graphene.Boolean()


class GenderType(DjangoObjectType):
    class Meta:
        model = Gender
        fields = "__all__"


class HostelType(DjangoObjectType):
    class Meta:
        model = Hostel
        fields = "__all__"


class StudentType(DjangoObjectType):
    class Meta:
        model = Student
        fields = "__all__"


class TransactionType(DjangoObjectType):
    display_date = (
        graphene.String()
    )  # display date in format 1 hour ago, 2 days ago etc

    class Meta:
        model = Transaction
        fields = [
            "status",
            "title",
            "amount",
            "desc",
            "_type",
            "created_at",
            "transaction_id",
            "display_date",
        ]

    def resolve_display_date(self, info):
        return convert_time_to_ago(self.created_at)


class TransactionNode(TransactionType, graphene.ObjectType):
    class Meta:
        model = Transaction
        interfaces = (graphene.relay.Node,)
        filterset_class = TransactionFilter


class VendorType(DjangoObjectType):
    profile = graphene.Field(ProfileType)
    store = graphene.Field("users.schema.StoreType")

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
        return self.user.user.profile

    def resolve_store(self, info):
        store = Store.objects.filter(vendor=self).first()
        return store


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
        try:
            return self.store_phone_numbers
        except:
            return []

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

    def resolve_store_cover_image(self, info):
        cover_image = None
        try:
            # get the cover image full url
            cover_image = info.context.build_absolute_uri(self.store_cover_image.url)
        except:
            pass
        return cover_image
