import graphene
from graphene_django.types import DjangoObjectType
from graphql_auth.schema import UserNode

from trayapp.utils import convert_time_to_ago

from users.filters import TransactionFilter, StoreFilter
from .models import (
    UserAccount,
    School,
    Student,
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
    store = graphene.Field("users.types.StoreType")
    gender = graphene.String()
    has_required_fields = graphene.Boolean()

    class Meta:
        model = Profile
        fields = "__all__"

    def resolve_image(self, info, *args, **kwargs):
        if self.image:
            image = info.context.build_absolute_uri(self.image.url)
        else:
            image = None
        return image

    def resolve_store(self, info, *args, **kwargs):
        # check if the user roles is student
        return self.store

    def resolve_gender(self, info, *args, **kwargs):
        if self.gender:
            return self.gender.name

    def resolve_has_required_fields(self, info, *args, **kwargs):
        return self.has_required_fields


class UserNodeType(UserNode, graphene.ObjectType):
    profile = graphene.Field(ProfileType)
    orders = graphene.List("product.types.OrderType")
    roles = graphene.List(graphene.String)

    class Meta:
        model = UserAccount
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "roles",
            "profile",
            "orders",
        ]

    def resolve_roles(self, info):
        return self.roles

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


class StoreOpenHours(graphene.ObjectType):
    day = graphene.String()
    open_time = graphene.String()
    close_time = graphene.String()


# store open hours input
class StoreOpenHoursInput(graphene.InputObjectType):
    day = graphene.String()
    open_time = graphene.String()
    close_time = graphene.String()


class StoreType(DjangoObjectType):
    store_country = graphene.String()
    store_categories = graphene.List(graphene.String)
    store_phone_numbers = graphene.List(graphene.String)
    store_image = graphene.String()
    store_cover_image = graphene.String()
    store_products = graphene.List("product.types.ItemType")
    store_menu = graphene.List(graphene.String)

    class Meta:
        model = Store
        fields = [
            "vendor",
            "store_name",
            "store_country",
            "store_type",
            "store_categories",
            "store_menu",
            "store_phone_numbers",
            "store_bio",
            "store_address",
            "store_nickname",
            "store_school",
            "store_image",
            "store_cover_image",
            "has_physical_store",
            "is_active",
            "store_products",
            "store_rank",
        ]

    def resolve_store_country(self, info):
        return self.store_country.name

    def resolve_store_categories(self, info):
        return self.store_categories

    def resolve_store_menu(self, info):
        store_menu = self.store_menu
        if store_menu is None:
            return []
        # arrange the menu json list from last to first
        store_menu.reverse()
        return store_menu

    def resolve_store_phone_numbers(self, info):
        try:
            return self.store_phone_numbers
        except:
            return []

    def resolve_store_products(self, info):
        return self.store_products.all()

    def resolve_store_image(self, info):
        vendor = self.vendor
        if vendor is None:
            return None
        image = None
        try:
            image = info.context.build_absolute_uri(vendor.image.url)
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


class StoreNode(StoreType, graphene.ObjectType):
    class Meta:
        model = Store
        interfaces = (graphene.relay.Node,)
        filterset_class = StoreFilter
