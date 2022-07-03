import graphene

from graphql_auth.schema import UserQuery, MeQuery
from graphql_auth import mutations

from users.mutations import CreateVendorMutation, EditVendorMutation

from .models import Client, Vendor, Store
from .types import ClientType, VendorType, StoreType


class Query(UserQuery, MeQuery, graphene.ObjectType):
    # vendors = DjangoFilterConnectionField(VendorType)
    vendors = graphene.List(VendorType)
    clients = graphene.List(ClientType)

    vendor = graphene.Field(VendorType, vendor_id=graphene.Int())
    client = graphene.Field(ClientType, client_id=graphene.Int())
    get_store = graphene.Field(StoreType, store_nickname=graphene.String())
    
    def resolve_vendors(self, info, **kwargs):
        # print(info.context.user)
        return Vendor.objects.all().order_by('-id')

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


class AuthMutation(graphene.ObjectType):
    register = mutations.Register.Field()
    update_account = mutations.UpdateAccount.Field()
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
    create_vendor = CreateVendorMutation.Field()
    update_vendor = EditVendorMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
