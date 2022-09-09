import graphene
from graphql import GraphQLError
from graphene_file_upload.scalars import Upload

from django.contrib.auth.models import User
from django.utils.module_loading import import_string

from graphql_jwt.refresh_token.shortcuts import get_refresh_token

from graphql_auth.schema import UserNode
from graphql_auth.mixins import UpdateAccountMixin
from graphql_auth.models import UserStatus
from graphql_auth.settings import graphql_auth_settings as app_settings

from .types import VendorType
from .models import Vendor, Store, Client, Hostel, Gender, Profile


if app_settings.EMAIL_ASYNC_TASK and isinstance(app_settings.EMAIL_ASYNC_TASK, str):
    async_email_func = import_string(app_settings.EMAIL_ASYNC_TASK)
else:
    async_email_func = None


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


class UpdateAccountMutation(UpdateAccountMixin, graphene.Mutation):
    class Arguments:
        token = graphene.String(required=True)
        username = graphene.String(required=True)
        first_name = graphene.String()
        last_name = graphene.String()
        email = graphene.String()
        phone_number = graphene.String()
        profile_image = Upload()

    user = graphene.Field(UserNode)

    __doc__ = UpdateAccountMixin.__doc__

    @staticmethod
    def mutate(self, info, token, username, first_name, email, last_name, phone_number=None, profile_image=None):
        user = info.context.user
        send_email = False
        if user.is_authenticated:
            token = get_refresh_token(token, info.context)
            if token:
                if token.user.username == user.username:
                    user = User.objects.filter(username=user.username).first()
                    if token and not user is None:
                        profile = Profile.objects.filter(user=user).first()
                        if not profile is None:
                            user.first_name = first_name
                            user.last_name = last_name
                            user.username = username
                            if profile_image:
                                profile.image = profile_image
                            if phone_number:
                                profile.phone_number = phone_number

                            profile.save()
                            if user.email != email:
                                send_email = True
                                user.status.verified = True

                            if send_email == True:
                                try:
                                    UserStatus.clean_email(email)
                                    # TODO CHECK FOR EMAIL ASYNC SETTING
                                    if async_email_func:
                                        async_email_func(
                                            user.status.send_activation_email, (info,))
                                    else:
                                        user.status.send_activation_email(info)
                                    user.email = email
                                except Exception as e:
                                    raise GraphQLError(
                                        "Error trying to send confirmation mail to %s" % email)
                            user.save()
                else:
                    user = None
                    raise GraphQLError(
                        "Authorized token required, Hope you know what you are doing...")
        else:
            user = None
            raise GraphQLError("Login required.")
        # Notice we return an instance of this mutation
        return UpdateAccountMutation(user=user)


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
