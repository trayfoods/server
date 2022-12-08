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
from graphql_auth.decorators import verification_required

from .types import VendorType  # , BankNode
from .models import Vendor, Store, Client, Hostel, Gender, Profile


if app_settings.EMAIL_ASYNC_TASK and isinstance(app_settings.EMAIL_ASYNC_TASK, str):
    async_email_func = import_string(app_settings.EMAIL_ASYNC_TASK)
else:
    async_email_func = None


class Output:
    """
    A class to all public classes extend to
    padronize the output
    """

    success = graphene.Boolean(default_value=True)


class CreateVendorMutation(Output, graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        store_name = graphene.String(required=True)
        store_nickname = graphene.String(required=True)
        store_category = graphene.String(required=True)

    # The class attributes define the response of the mutation
    vendor = graphene.Field(VendorType)
    user = graphene.Field(UserNode)

    @staticmethod
    def mutate(self, info, store_name, store_category, store_nickname):
        success = False
        if info.context.user.is_authenticated:
            vendor = Vendor.objects.filter(
                user=info.context.user.profile).first()  # get the vendor
            if vendor is None:
                store_check = Store.objects.filter(
                    store_nickname=store_nickname.strip()).first()  # check if the store nickname is already taken
                if store_check is None:  # if not taken
                    store = Store.objects.create(
                        store_name=store_name,
                        store_nickname=store_nickname,
                        store_category=store_category
                    )  # create the store
                    store.save()
                    vendor = Vendor.objects.create(
                        user=info.context.user.profile,
                        store=store)
                    vendor.save()
                    success = True
                else:  # if taken
                    raise GraphQLError(
                        "Store Nickname Already Exists, Please use a unique name")  # raise error
            else:  # if vendor already exists
                success = False
                raise GraphQLError('You Already A Vendor')  # raise error
        else:  # if user is not authenticated
            raise GraphQLError("Login required.")  # raise error
        # Notice we return an instance of this mutation
        return CreateVendorMutation(user=info.context.user, vendor=vendor)

    @verification_required
    def resolve_mutation(cls, root, info, **kwargs):
        user = info.context.user
        if user.profile and user.vendor:
            return cls(success=True)
        else:
            return cls(success=False)


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
            vendor = Vendor.objects.get(pk=id)  # get the vendor
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


class CreateClientMutation(Output, graphene.Mutation):
    class Arguments:
        hostel_shortname = graphene.String(required=False)
        room = graphene.String(required=False)
        gender = graphene.String(required=True)

    user = graphene.Field(UserNode)

    @staticmethod
    def mutate(self, info, gender, hostel_shortname=None, room=None):
        user = info.context.user
        profile = info.context.user.profile
        if user.is_authenticated:
            vendor = Vendor.objects.filter(
                user=profile).first()  # get the vendor
            if vendor is None:
                client = Client.objects.filter(
                    user=profile).first()  # get the client
                if client is None:  # if client does not exist
                    hostel = Hostel.objects.filter(
                        short_name=hostel_shortname).first()  # get the hostel
                    gender = gender.upper()
                    gender = Gender.objects.filter(name=gender).first()
                    if not gender is None:
                        gender.rank += 1  # increment the rank
                        gender.save()
                        new_client = Client.objects.create(
                            user=profile, hostel=hostel, room=room)  # create the client
                        new_client_profile = Profile.objects.filter(
                            user=user).first()  # get the profile
                        if not new_client_profile is None:  # if profile exists
                            new_client_profile.gender = gender
                            new_client_profile.save()  # save the profile
                        new_client.save()
                        user = User.objects.get(
                            username=user.username)  # set the client
                    else:
                        # raise error if gender does not exist
                        raise GraphQLError("Gender do not exists")
        else:
            raise GraphQLError("Login Required.")
        return CreateClientMutation(user=info.context.user)

    @verification_required
    def resolve_mutation(cls, root, info, **kwargs):
        user = info.context.user
        if user.profile and user.client:
            return cls(success=True)
        else:
            return cls(success=False)


class EmailVerifiedCheckerMutation(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)

    # The class attributes define the response of the mutation
    is_verified = graphene.Boolean()
    error = graphene.String()

    @staticmethod
    def mutate(self, info, email):
        is_verified = False  # the user email is not verified
        error = None
        user = User.objects.filter(email=email).first()  # get the user
        if not user is None:
            user_status = UserStatus.objects.filter(
                user=user).first()  # get the user status
            if user_status.verified == True:  # check if the user email is verified
                is_verified = True  # the user email is verified
            else:
                is_verified = False
        else:  # the user does not exist
            error = "email do not exists"
        return EmailVerifiedCheckerMutation(is_verified=is_verified, error=error)


class UpdateVendorBankAccount(Output, graphene.Mutation):
    class Arguments:
        account_number = graphene.String(required=True)
        account_name = graphene.String(required=True)
        bank_code = graphene.String(required=True)

    # The class attributes define the response of the mutation
    error = graphene.String()

    @staticmethod
    def mutate(self, info, account_number, account_name, bank_code):
        success = False
        error = None
        user = info.context.user
        if user.is_authenticated:  # check if the user is authenticated
            profile = Profile.objects.filter(
                user=user).first()  # get the profile
            if not profile is None:  # check if the profile exists
                vendor = Vendor.objects.filter(
                    user=profile).first()  # get the vendor
                if not vendor is None:
                    vendor.account_number = account_number
                    vendor.account_name = account_name
                    vendor.bank_code = bank_code
                    vendor.save()
                    success = True
                else:  # the vendor does not exist
                    error = "Vendor do not exist"
            else:  # the profile does not exist
                error = "Profile do not exist"
        else:  # the user is not authenticated
            error = "Login required"
        return UpdateVendorBankAccount(success=success, error=error)
