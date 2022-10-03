import graphene
from django.contrib.auth import get_user_model
from graphql_auth.schema import UserNode, MeQuery
from graphql_auth import mutations

from users.mutations import (CreateVendorMutation, EditVendorMutation, UpdateVendorBankAccount,
                             UpdateAccountMutation, CreateClientMutation, EmailVerifiedCheckerMutation)
from .models import Client, Vendor, Store, Hostel
from .types import ClientType, VendorType, StoreType, HostelType
from django.db.models import Q

from users.custom_model import BankListQuery

User = get_user_model()


class Query(MeQuery, BankListQuery, graphene.ObjectType):
    # vendors = DjangoFilterConnectionField(VendorType)
    get_user = graphene.Field(UserNode, username=graphene.String())
    vendors = graphene.List(VendorType)
    clients = graphene.List(ClientType)
    hostels = graphene.List(HostelType)

    vendor = graphene.Field(VendorType, vendor_id=graphene.Int())
    client = graphene.Field(ClientType, client_id=graphene.Int())
    get_store = graphene.Field(StoreType, store_nickname=graphene.String())
    search_stores = graphene.Field(StoreType, search_query=graphene.String(
        required=True), count=graphene.Int(required=False))

    def resolve_get_user(self, info, username):
        return User.objects.get(username=username)

    def resolve_vendors(self, info, **kwargs):
        return Vendor.objects.all().order_by('-id')

    def resolve_hostels(self, info, **kwargs):
        return Hostel.objects.all()

    def resolve_vendor(self, info, vendor_id):
        return Vendor.objects.get(pk=vendor_id)

    def resolve_clients(self, info, **kwargs):
        if not info.context.user.is_authenticated():
            return Client.objects.none()
        else:
            return Client.objects.all().order_by('-id')

    def resolve_client(self, info, client_id):
        return Client.objects.get(pk=client_id)

    def resolve_get_store(self, info, store_nickname):
        store = Store.objects.filter(store_nickname=store_nickname).first()
        if not store is None:
            store.store_rank += 0.5
            store.save()
        return store

    def resolve_search_stores(self, info, search_query, count=None):
        stores_list = Store.objects.filter(store_nickname=search_query).first()
        if count:
            if stores_list.count() >= count:
                stores_list = stores_list[:count]
        else:
            stores_list = stores_list[:20]
        return stores_list


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
    check_email_verification = EmailVerifiedCheckerMutation.Field()
    update_vendor_bank_details = UpdateVendorBankAccount.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
