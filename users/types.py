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
    DeliveryPerson,
    HostelField,
)


class SchoolType(DjangoObjectType):
    campuses = graphene.List(graphene.String)

    class Meta:
        model = School
        fields = "__all__"

    def resolve_campuses(self, info):
        return self.campuses


class HostelFieldType(DjangoObjectType):
    options = graphene.List(graphene.String)

    class Meta:
        model = HostelField
        fields = "__all__"

    def resolve_options(self: HostelField, info):
        return self.get_options()


class ProfileType(DjangoObjectType):
    store = graphene.Field("users.types.StoreType")
    gender = graphene.String()
    required_fields = graphene.List(graphene.String)
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

    def resolve_required_fields(self, info, *args, **kwargs):
        return self.get_required_fields()

    def resolve_has_required_fields(self, info, *args, **kwargs):
        return self.get_required_fields() is not None and len(self.get_required_fields()) > 0


class UserSettingsType(graphene.ObjectType):
    has_token_device = graphene.Boolean()
    hide_wallet_balance = graphene.Boolean()

    def resolve_has_token_device(self, info, *args, **kwargs):
        return self.has_token_device
    
    def resolve_hide_wallet_balance(self, info):
        user = info.context.user
        profile_wallet = user.profile.get_wallet()

        if user.is_authenticated and profile_wallet:
            return profile_wallet.hide_balance
        
        return False


class UserNodeType(UserNode, graphene.ObjectType):
    profile = graphene.Field(ProfileType)
    orders = graphene.List("product.types.OrderType")
    roles = graphene.List(graphene.String)
    settings = graphene.Field("users.types.UserSettingsType")

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
            "settings",
        ]

    def resolve_roles(self, info):
        return self.roles

    def resolve_orders(self, info):
        return self.orders.all()

    def resolve_profile(self, info):
        return self.profile

    def resolve_settings(self, info):
        return self


class GenderType(DjangoObjectType):
    class Meta:
        model = Gender
        fields = "__all__"


class HostelType(DjangoObjectType):
    class Meta:
        model = Hostel
        fields = "__all__"


class StudentHostelFieldType(graphene.ObjectType):
    field_id = graphene.String()
    value = graphene.String()


class StudentType(DjangoObjectType):
    hostel_fields = graphene.List(StudentHostelFieldType)
    hostel_address = graphene.String()

    class Meta:
        model = Student
        fields = "__all__"

    def resolve_hostel_fields(self, info):
        return self.hostel_fields

    def resolve_hostel_address(self, info):
        # get all the hostel fields values and append them to the address
        hostel_fields = self.hostel_fields
        hostel_address = ""
        for field in hostel_fields:
            hostel_fields_qs = HostelField.objects.filter(id=field["field_id"])
            if hostel_fields_qs.count() > 0:
                value_prefix = hostel_fields_qs.first().value_prefix
                hostel_address += f"{value_prefix if value_prefix else "" } {field["value"]} - "
            else:
                hostel_address += f"{field["value"]} - "
            hostel_address = hostel_address.strip()
            # remove - if it is the last character
            if hostel_address[-1] == "-":
                hostel_address = hostel_address[:-1]
        return hostel_address


class TransactionType(DjangoObjectType):
    display_date = (
        graphene.String()
    )  # display date in format 1 hour ago, 2 days ago etc
    order_display_id = graphene.String(default_value=None)

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
            "order_url"
        ]

    def resolve_display_date(self, info):
        return convert_time_to_ago(self.created_at)
    
    def resolve_order_display_id(self: Transaction, info):
        is_order_transaction = self.order is not None
        if is_order_transaction:
            return self.order.get_order_display_id()
        return None


class TransactionNode(TransactionType, graphene.ObjectType):
    class Meta:
        model = Transaction
        interfaces = (graphene.relay.Node,)
        filterset_class = TransactionFilter


class StoreOpenHours(graphene.ObjectType):
    day = graphene.String()
    open_time = graphene.String()
    close_time = graphene.String()

class AveragePreparationTime:
    min = graphene.Int()
    max = graphene.Int()

class AveragePreparationTimeType(AveragePreparationTime, graphene.ObjectType):
    pass

class AveragePreparationTimeInput(AveragePreparationTime, graphene.InputObjectType):
    pass





# store open hours input
class StoreOpenHoursInput(graphene.InputObjectType):
    day = graphene.String()
    open_time = graphene.String()
    close_time = graphene.String()


class StoreType(DjangoObjectType):
    store_id = graphene.String()
    store_categories = graphene.List(graphene.String)
    store_image = graphene.String()
    store_cover_image = graphene.String()
    store_items = graphene.List("product.types.ItemType")
    store_menu = graphene.List(graphene.String)
    store_open_hours = graphene.List(StoreOpenHours)
    store_average_preparation_time = graphene.Field(AveragePreparationTimeType)
    whatsapp_numbers = graphene.List(graphene.String)

    country = graphene.String()
    country_code = graphene.String()

    class Meta:
        model = Store
        fields = "__all__"

    def resolve_store_id(self, info):
        return self.id

    def resolve_store_categories(self, info):
        return self.store_categories

    def resolve_store_menu(self, info):
        store_menu = self.store_menu
        if store_menu is None:
            return []
        return store_menu

    def resolve_store_items(self, info):
        return self.get_store_products()[:11]

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

    def resolve_store_open_hours(self, info):
        return self.store_open_hours
    
    def resolve_store_average_preparation_time(self, info):
        return self.store_average_preparation_time

    def resolve_whatsapp_numbers(self, info):
        return self.whatsapp_numbers

    def resolve_country(self, info):
        return self.country.name
    
    def resolve_country_code(self, info):
        return self.country.code


class StoreNode(StoreType, graphene.ObjectType):
    class Meta:
        model = Store
        interfaces = (graphene.relay.Node,)
        filterset_class = StoreFilter

class StoreItmMenuType(graphene.ObjectType):
    menu = graphene.String()
    items = graphene.List("product.types.ItemType")

class DeliveryPersonType(DjangoObjectType):
    class Meta:
        model = DeliveryPerson
        fields = "__all__"

class WalletNode(graphene.ObjectType):
    balance = graphene.String()
    unsettled_balance = graphene.String()
    error = graphene.String(default_value=None)
    success = graphene.Boolean(default_value=False)
