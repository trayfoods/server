import graphene
from graphql import GraphQLError
from graphene_file_upload.scalars import Upload

from django.utils.module_loading import import_string

from graphql_auth.mixins import UpdateAccountMixin
from graphql_auth.models import UserStatus
from graphql_auth.settings import graphql_auth_settings as app_settings
from graphql_auth.decorators import verification_required
from trayapp.permissions import IsAuthenticated, permission_checker

from .types import StoreType, VendorType, UserNodeType  # , BankNode
from .models import (
    Vendor,
    Store,
    School,
    Client,
    Hostel,
    Gender,
    Profile,
    UserAccount,
)

User = UserAccount

if app_settings.EMAIL_ASYNC_TASK and isinstance(app_settings.EMAIL_ASYNC_TASK, str):
    async_email_func = import_string(app_settings.EMAIL_ASYNC_TASK)
else:
    async_email_func = None


class Output:
    """
    A class to all public classes extend to
    padronize the output
    """

    success = graphene.Boolean(default_value=False)


class CreateStoreMutation(Output, graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        store_name = graphene.String(required=True)
        store_country = graphene.String(required=True)
        store_address = graphene.String(required=True)
        store_type = graphene.String(required=True)
        store_categories = graphene.List(graphene.String, required=True)
        store_phone_numbers = graphene.List(graphene.String, required=True)
        store_bio = graphene.String(required=False)
        store_nickname = graphene.String(required=True)
        store_school = graphene.String(required=True)

    # The class attributes define the response of the mutation
    store = graphene.Field(StoreType)
    user = graphene.Field(UserNodeType)

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(
        self,
        info,
        store_name,
        store_country,
        store_address,
        store_type,
        store_categories,
        store_phone_numbers,
        store_bio,
        store_nickname,
        store_school,
    ):
        success = False
        user = info.context.user

        user = User.objects.get(username=user.username)
        profile = user.profile
        vendor = Vendor.objects.filter(user=profile).first()  # get the vendor
        if vendor is None:
            store_check = Store.objects.filter(
                store_nickname=store_nickname.strip()
            ).first()  # check if the store nickname is already taken
            if store_check is None:  # if not taken
                vendor = Vendor.objects.create(user=profile)
                store_school_qs = School.objects.filter(slug=store_school.strip())
                if not store_school_qs.exists():
                    raise GraphQLError("School does not exist, please try again")
                vendor.save()
                store = Store.objects.create(
                    store_name=store_name,
                    store_country=store_country,
                    store_address=store_address,
                    store_type=store_type,
                    store_categories=store_categories,
                    store_phone_numbers=store_phone_numbers,
                    store_bio=store_bio,
                    store_nickname=store_nickname,
                    store_school=store_school_qs.first(),
                    vendor=vendor,
                )  # create the store
                store.save()
                user.role = "vendor"  # do not touch
                user.save()

                success = True

                # return the vendor and user
                return CreateStoreMutation(success=success, user=user, store=store)
            else:  # if taken
                raise GraphQLError(
                    "Store Nickname Already Exists, Please use a unique name"
                )  # raise error
        else:  # if vendor already exists
            success = False
            raise GraphQLError("You Already A Vendor")  # raise error

    @verification_required
    def resolve_mutation(cls, root, info, **kwargs):
        user = info.context.user
        # check if the store is was not created then delete the vendor
        if user.vendor and not user.vendor.store:
            user.vendor.delete()
        if user.profile and user.vendor:
            return cls(success=True, user=user, store=user.vendor.store)
        else:
            store = Store.objects.filter(vendor=user.vendor).first()
            return cls(success=False, user=user, store=store)


class UpdateAccountMutation(UpdateAccountMixin, graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        first_name = graphene.String()
        last_name = graphene.String()
        email = graphene.String()
        phone_number = graphene.String()
        profile_image = Upload()

    user = graphene.Field(UserNodeType)

    __doc__ = UpdateAccountMixin.__doc__

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(
        self,
        info,
        username,
        first_name,
        email,
        last_name,
        phone_number=None,
        profile_image=None,
    ):
        user = info.context.user
        send_email = False
        profile = user.profile
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
                    async_email_func(user.status.send_activation_email, (info,))
                else:
                    user.status.send_activation_email(info)
                user.email = email
            except Exception as e:
                raise GraphQLError(
                    "Error trying to send confirmation mail to %s" % email
                )
        user.save()
        # Notice we return an instance of this mutation
        return UpdateAccountMutation(user=user)


class UpdateStoreMutation(graphene.Mutation):
    class Arguments:
        store_name = graphene.String(required=True)
        store_country = graphene.String(required=True)
        store_address = graphene.String(required=True)
        store_type = graphene.String(required=True)
        store_categories = graphene.List(graphene.String, required=True)
        store_phone_numbers = graphene.List(graphene.String, required=True)
        store_bio = graphene.String(required=True)
        store_nickname = graphene.String(required=True)
        store_school = graphene.String(required=True)

    # The class attributes define the response of the mutation
    success = graphene.Boolean()
    error = graphene.String()
    store = graphene.Field(StoreType)

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(
        self,
        info,
        store_name,
        store_country,
        store_address,
        store_type,
        store_categories,
        store_phone_numbers,
        store_bio,
        store_nickname,
        store_school,
    ):
        success = False
        error = None
        user = info.context.user
        profile = user.profile
        vendor = Vendor.objects.filter(user=profile).first()  # get the vendor
        if vendor is None:
            store = Store.objects.filter(vendor=vendor).first()
            if not store is None:
                store.store_name = store_name
                store.store_country = store_country
                store.store_address = store_address
                store.store_type = store_type
                store.store_categories = store_categories
                store.store_phone_numbers = store_phone_numbers
                store.store_bio = store_bio
                store.store_nickname = store_nickname
                store.store_school = store_school
                store.save()
                success = True
            else:
                error = "Store does not exist"
        else:
            error = "You are not a vendor"
        return UpdateStoreMutation(success=success, error=error, store=store)


class CreateClientMutation(Output, graphene.Mutation):
    class Arguments:
        hostel_shortname = graphene.String(required=False)
        room = graphene.String(required=False)
        gender = graphene.String(required=True)

    user = graphene.Field(UserNodeType)

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(self, info, gender, hostel_shortname=None, room=None):
        user = info.context.user
        profile = info.context.user.profile
        if user.is_authenticated:
            vendor = Vendor.objects.filter(user=profile).first()  # get the vendor
            if vendor is None:
                client = Client.objects.filter(user=profile).first()  # get the client
                if client is None:  # if client does not exist
                    hostel = Hostel.objects.filter(
                        short_name=hostel_shortname
                    ).first()  # get the hostel
                    gender = gender.upper()
                    gender = Gender.objects.filter(name=gender).first()
                    if not gender is None:
                        gender.rank += 1  # increment the rank
                        gender.save()
                        new_client = Client.objects.create(
                            user=profile, hostel=hostel, room=room
                        )  # create the client
                        new_client_profile = Profile.objects.filter(
                            user=user
                        ).first()  # get the profile
                        if not new_client_profile is None:  # if profile exists
                            new_client_profile.gender = gender
                            new_client_profile.save()  # save the profile
                        new_client.save()
                        user = User.objects.filter(username=user.username).first()
                        if not user is None:
                            user.role = "student"  # do not touch
                            user.save()
                    else:
                        # raise error if gender does not exist
                        raise GraphQLError("Gender do not exists")
        else:
            raise GraphQLError("Login Required.")
        return CreateClientMutation(user=user)

    @verification_required
    def resolve_mutation(cls, root, info, **kwargs):
        user = info.context.user
        if user.profile and user.client:
            return cls(success=True, user=user)
        else:
            return cls(success=False, user=user)


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
                user=user
            ).first()  # get the user status
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
    @permission_checker([IsAuthenticated])
    def mutate(self, info, account_number, account_name, bank_code):
        success = False
        error = None
        user = info.context.user
        if user.is_authenticated:  # check if the user is authenticated
            profile = Profile.objects.filter(user=user).first()  # get the profile
            if not profile is None:  # check if the profile exists
                vendor = Vendor.objects.filter(user=profile).first()  # get the vendor
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


class UserDeviceMutation(Output, graphene.Mutation):
    class Arguments:
        device_token = graphene.String(required=True)
        action = graphene.String(required=True)
        device_type = graphene.String(required=False)
        device_name = graphene.String(required=False)

    # The class attributes define the response of the mutation
    error = graphene.String()

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(self, info, device_token, action, device_type=None, device_name=None):
        # check if action is in the list of actions
        list_of_actions = ["add", "remove"]
        if not action in list_of_actions:
            raise GraphQLError("Invalid action")
        success = False
        error = None
        user = info.context.user
        user_devices = user.devices.all()
        # check if the device token and device type exists in the user devices
        device = user_devices.filter(
            device_token=device_token, device_type=device_type, device_name=device_name
        )
        if not device.exists() and action == "add":
            user.add_device(
                **{
                    "device_token": device_token,
                    "device_type": device_type,
                    "device_name": device_name,
                }
            )
            success = True
        elif action == "remove":
            if device.exists():
                device = device.first()
                device.delete()
                success = True
            else:
                error = "Device token does not exist"
        else:
            error = "Device token already exists"
        return UserDeviceMutation(success=success, error=error)
