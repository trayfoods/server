import graphene
from django.contrib.auth import get_user_model
from graphql_auth import mutations
from django.db.models import Q
import requests

from trayapp.utils import paginate_queryset
from .mutations import (
    CreateVendorMutation,
    EditVendorMutation,
    UpdateVendorBankAccount,
    UpdateAccountMutation,
    CreateClientMutation,
    UserDeviceMutation,
)
from .models import Client, Vendor, Store, Hostel
from .types import (
    ClientType,
    VendorType,
    StoreType,
    HostelType,
    UserNodeType,
    IPInfoType,
)
from graphql_auth.models import UserStatus

from trayapp.custom_model import BankListQuery, EmailVerifiedNode, UniversityNode

import universities

User = get_user_model()


class Query(BankListQuery, graphene.ObjectType):
    ip_info = graphene.Field(IPInfoType)
    me = graphene.Field(UserNodeType)
    vendors = graphene.List(VendorType)
    # clients = graphene.List(ClientType)
    hostels = graphene.List(HostelType)

    check_email_verification = graphene.Field(
        EmailVerifiedNode, email=graphene.String()
    )

    vendor = graphene.Field(VendorType, vendor_id=graphene.Int())

    client = graphene.Field(ClientType, client_id=graphene.Int())
    get_store = graphene.Field(StoreType, store_nickname=graphene.String())
    search_stores = graphene.Field(
        StoreType,
        search_query=graphene.String(required=True),
        count=graphene.Int(required=False),
    )

    get_trending_stores = graphene.List(
        StoreType, count=graphene.Int(required=False), page=graphene.Int(required=True)
    )

    get_universities = graphene.List(
        UniversityNode, query=graphene.String(required=True), country=graphene.String()
    )

    def resolve_ip_info(self, info):
        from ipware import get_client_ip

        ip, is_routable = get_client_ip(info.context)
        is_vpn = not is_routable

        # Get country information from ipinfo.io API
        country = None
        if ip:
            response = requests.get(f"https://ipinfo.io/{ip}/country")
            if response.status_code == 200:
                country = response.text.strip()

        return IPInfoType(ip_address=ip, is_vpn=is_vpn, country=country)

    def resolve_get_universities(self, info, query, country=None):
        uni = universities.API()
        if country:
            return uni.search(country=country, name=query)
        return uni.search(name=query)

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
        return Client.objects.get(pk=client_id)

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


class AuthMutation(graphene.ObjectType):
    register = mutations.Register.Field()
    verify_account = mutations.VerifyAccount.Field()
    resend_activation_email = mutations.ResendActivationEmail.Field()
    send_password_reset_email = mutations.SendPasswordResetEmail.Field()
    password_reset = mutations.PasswordReset.Field()
    password_change = mutations.PasswordChange.Field()

    # django-graphql-jwt inheritances
    token_auth = mutations.ObtainJSONWebToken.Field()
    verify_token = mutations.VerifyToken.Field()
    refresh_token = mutations.RefreshToken.Field()
    revoke_token = mutations.RevokeToken.Field()


class Mutation(AuthMutation, graphene.ObjectType):
    update_account = UpdateAccountMutation.Field()
    create_vendor = CreateVendorMutation.Field()
    create_client = CreateClientMutation.Field()
    update_vendor = EditVendorMutation.Field()
    update_vendor_bank_details = UpdateVendorBankAccount.Field()
    user_device = UserDeviceMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
