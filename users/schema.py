import graphene
from django.contrib.auth import get_user_model
from graphql import GraphQLError
from graphql_auth import mutations
from django.db.models import Q
from users.queries.transactions import TransactionQueries

from trayapp.utils import paginate_queryset
from .mutations import (
    CreateStoreMutation,
    UpdateStoreMutation,
    UpdateVendorBankAccount,
    UpdateAccountMutation,
    CreateClientMutation,
    UserDeviceMutation,
    LoginMutation,
    RegisterMutation,
)
from .models import Student, Vendor, Store, Hostel, School
from .types import (
    StudentType,
    VendorType,
    StoreType,
    HostelType,
    UserNodeType,
    SchoolType,
)
from graphql_auth.models import UserStatus

from trayapp.custom_model import BankListQuery, EmailVerifiedNode

User = get_user_model()


class Query(BankListQuery, TransactionQueries, graphene.ObjectType):
    me = graphene.Field(UserNodeType)
    vendors = graphene.List(VendorType)
    # clients = graphene.List(StudentType)
    hostels = graphene.List(HostelType)

    check_email_verification = graphene.Field(
        EmailVerifiedNode, email=graphene.String()
    )

    vendor = graphene.Field(VendorType, vendor_id=graphene.Int())

    client = graphene.Field(StudentType, client_id=graphene.Int())
    get_store = graphene.Field(StoreType, store_nickname=graphene.String())
    search_stores = graphene.Field(
        StoreType,
        search_query=graphene.String(required=True),
        count=graphene.Int(required=False),
    )

    get_trending_stores = graphene.List(
        StoreType, count=graphene.Int(required=False), page=graphene.Int(required=True)
    )

    schools = graphene.List(
        SchoolType,
        name=graphene.String(required=False),
        country=graphene.String(required=False),
        count=graphene.Int(required=False),
    )

    school = graphene.Field(
        SchoolType,
        slug=graphene.String(required=True),
    )

    def resolve_get_trending_stores(self, info, page, count=None, page_size=10):
        """
        Resolve the get_trending_stores query.

        Args:
            info: The GraphQL ResolveInfo object.
            page: The page number for pagination.
            count: The maximum number of stores to return.
            page_size: The number of stores to display per page.

        Returns:
            A paginated queryset of trending stores.
        """
        stores_list = Store.objects.all().order_by("-store_rank")
        # check if each store products are up to 2
        for store in stores_list:
            if store.store_products.count() < 2:
                stores_list = stores_list.exclude(pk=store.pk)
        if count is not None:
            if stores_list.count() >= count:
                stores_list = stores_list[:count]
        else:
            stores_list = stores_list
        paginated_queryset = paginate_queryset(stores_list, page_size, page)
        return paginated_queryset

    def resolve_me(self, info):
        user = info.context.user
        if user.is_authenticated:
            return user
        return None

    def resolve_vendors(self, info, **kwargs):
        return Vendor.objects.all().order_by("-id")

    def resolve_hostels(self, info, **kwargs):
        return Hostel.objects.all()

    def resolve_vendor(self, info, vendor_id):
        return Vendor.objects.get(pk=vendor_id)

    def resolve_client(self, info, client_id):
        return Student.objects.get(pk=client_id)

    def resolve_get_store(self, info, store_nickname):
        store = Store.objects.filter(store_nickname=store_nickname).first()
        if not store is None:
            store.store_rank += 0.5
            store.save()
        return store

    def resolve_search_stores(self, info, search_query, count=None):
        stores_list = Store.objects.filter(
            Q(store_nickname__icontains=search_query)
        ).first()
        if count:
            if stores_list.count() >= count:
                stores_list = stores_list[:count]
        else:
            stores_list = stores_list[:20]
        return stores_list

    def resolve_check_email_verification(self, info, email):
        data = {"success": False, "msg": None}
        user = User.objects.filter(email=email).first()  # get the user
        if not user is None:
            user_status = UserStatus.objects.filter(
                user=user
            ).first()  # get the user status
            if user_status.verified == True:  # check if the user email is verified
                data["success"] = True  # the user email is verified
            else:
                data["success"] = False
        else:  # the user does not exist
            data["msg"] = "email do not exists"
        return data

    def resolve_schools(self, info, name=None, country=None, count=None):
        schools = []

        # check if country and name is not None
        if name and country:
            schools = School.objects.filter(
                Q(name__icontains=name) | Q(country__icontains=country)
            )

        if name is None and country is None:
            raise GraphQLError("name and country cannot be None")

        if name:
            schools = School.objects.filter(name__icontains=name)
        if country:
            schools = School.objects.filter(country__icontains=country)

        if count:
            schools = schools[:count]

        return schools

    def resolve_school(self, info, slug):
        school = School.objects.filter(slug=slug).first()
        if school is None:
            raise GraphQLError("school does not exist")
        return school


class AuthMutation(graphene.ObjectType):
    register = RegisterMutation.Field()
    verify_account = mutations.VerifyAccount.Field()
    resend_activation_email = mutations.ResendActivationEmail.Field()
    send_password_reset_email = mutations.SendPasswordResetEmail.Field()
    password_reset = mutations.PasswordReset.Field()
    password_change = mutations.PasswordChange.Field()

    # django-graphql-jwt inheritances
    token_auth = LoginMutation.Field()
    verify_token = mutations.VerifyToken.Field()
    refresh_token = mutations.RefreshToken.Field()
    revoke_token = mutations.RevokeToken.Field()


class Mutation(AuthMutation, graphene.ObjectType):
    update_account = UpdateAccountMutation.Field()
    create_store = CreateStoreMutation.Field()
    update_store = UpdateStoreMutation.Field()
    create_client = CreateClientMutation.Field()
    update_vendor_bank_details = UpdateVendorBankAccount.Field()
    user_device = UserDeviceMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
