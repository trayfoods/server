import graphene
from graphql import GraphQLError
from .types import VendorType
from .models import Vendor, Store, Client, Hostel, Gender, Profile
# from django.contrib.auth.models import User
from graphql_auth.schema import UserNode


class CreateVendorMutation(graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        store_name = graphene.String(required=True)
        store_nickname = graphene.String(required=True)
        store_category = graphene.String(required=True)

    # The class attributes define the response of the mutation
    vendor = graphene.Field(VendorType)
    user = graphene.Field(UserNode)
    success = graphene.Boolean()

    @staticmethod
    def mutate(self, info, store_name, store_category, store_nickname):
        success = False
        if info.context.user.is_authenticated:
            vendor = Vendor.objects.filter(
                user=info.context.user.profile).first()
            if vendor is None:
                store_check = Store.objects.filter(
                    store_nickname=store_nickname.strip()).first()
                if store_check is None:
                    store = Store.objects.create(
                        store_name=store_name,
                        store_nickname=store_nickname,
                        store_category=store_category
                    )
                    store.save()
                    vendor = Vendor.objects.create(
                        user=info.context.user.profile,
                        store=store)
                    vendor.save()
                    success = True
                else:
                    raise GraphQLError(
                        "Store Nickname Already Exists, Please use a unique name")
            else:
                success = False
                raise GraphQLError('You Already A Vendor')
        else:
            raise GraphQLError("Login required.")
        # Notice we return an instance of this mutation
        return CreateVendorMutation(user=info.context.user, vendor=vendor, success=success)


class EditVendorMutation(graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        id = graphene.ID()
        full_name = graphene.String()
        gender = graphene.String()
        phone_number = graphene.String()
        email = graphene.String()

    # The class attributes define the response of the mutation
    vendor = graphene.Field(VendorType)
    success = graphene.Boolean()

    @staticmethod
    def mutate(self, info, id, full_name, gender, phone_number, email):
        success = False
        if info.context.user.is_authenticated:
            vendor = Vendor.objects.get(pk=id)
            vendor.full_name = full_name
            vendor.gender = gender
            vendor.phone_number = phone_number
            vendor.email = email
            vendor.save()
            success = True
        else:
            raise GraphQLError("Login required.")
        # Notice we return an instance of this mutation
        return EditVendorMutation(vendor=vendor, success=success)


class CreateClientMutation(graphene.Mutation):
    class Arguments:
        hostel_shortname = graphene.String(required=False)
        room = graphene.String(required=False)
        gender = graphene.String(required=True)

    success = graphene.Boolean()
    user = graphene.Field(UserNode)

    def mutate(self, info, gender, hostel_shortname=None, room=None):
        success = False
        user = info.context.user
        profile = info.context.user.profile
        if user.is_authenticated:
            vendor = Vendor.objects.filter(
                user=profile).first()
            if vendor is None:
                client = Client.objects.filter(
                    user=profile).first()
                if client is None:
                    hostel = Hostel.objects.filter(
                        short_name=hostel_shortname).first()
                    gender = gender.upper()
                    gender = Gender.objects.filter(name=gender).first()
                    if not gender is None:
                        gender.rank += 0.1
                        gender.save()
                        new_client = Client.objects.create(
                            user=profile, hostel=hostel, room=room)
                        new_client_profile = Profile.objects.filter(
                            user=user).first()
                        if not new_client_profile is None:
                            new_client_profile.gender = gender
                            new_client_profile.save()
                        new_client.save()
                        success = True
                    else:
                        raise GraphQLError("Gender do not exists")
        else:
            raise GraphQLError("Login Required.")
        return CreateClientMutation(user=info.context.user, success=success)
