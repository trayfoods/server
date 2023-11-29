import requests
import json

import graphene
from graphql import GraphQLError
from graphene_file_upload.scalars import Upload
from django.utils.module_loading import import_string

from graphql_auth.mixins import UpdateAccountMixin
from graphql_auth.models import UserStatus
from graphql_auth.decorators import verification_required
from trayapp.utils import calculate_tranfer_fee
from users.mixins import RegisterMixin, ObtainJSONWebTokenMixin
from trayapp.permissions import IsAuthenticated, permission_checker

from .types import UserNodeType
from .models import (
    Transaction,
    Store,
    School,
    Student,
    Hostel,
    Gender,
    Profile,
    UserAccount,
    Wallet,
)
from product.models import Order
from django.conf import settings
from core.utils import get_paystack_balance
import uuid

User = UserAccount
PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY

if settings.EMAIL_ASYNC_TASK and isinstance(settings.EMAIL_ASYNC_TASK, str):
    async_email_func = import_string(settings.EMAIL_ASYNC_TASK)
else:
    async_email_func = None


class Output:
    """
    A class to all public classes extend to
    padronize the output
    """

    success = graphene.Boolean(default_value=False)
    error = graphene.String(default_value=None)


import graphql_jwt
from graphql_auth.utils import normalize_fields
from graphql_auth.bases import MutationMixin, DynamicArgsMixin
from graphql_auth.settings import graphql_auth_settings as app_settings


class RegisterMutation(
    MutationMixin, DynamicArgsMixin, RegisterMixin, graphene.Mutation
):
    __doc__ = RegisterMixin.__doc__
    _required_args = normalize_fields(
        app_settings.REGISTER_MUTATION_FIELDS, ["password1", "password2"]
    )
    _args = app_settings.REGISTER_MUTATION_FIELDS_OPTIONAL


class LoginMutation(
    MutationMixin, ObtainJSONWebTokenMixin, graphql_jwt.JSONWebTokenMutation
):
    __doc__ = ObtainJSONWebTokenMixin.__doc__
    user = graphene.Field(UserNodeType)
    unarchiving = graphene.Boolean(default_value=False)

    @classmethod
    def Field(cls, *args, **kwargs):
        cls._meta.arguments.update({"password": graphene.String(required=True)})
        for field in app_settings.LOGIN_ALLOWED_FIELDS:
            cls._meta.arguments.update({field: graphene.String()})
        return super(graphql_jwt.JSONWebTokenMutation, cls).Field(*args, **kwargs)


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
        if profile.store is None:
            store_check = Store.objects.filter(
                store_nickname=store_nickname.strip()
            ).first()  # check if the store nickname is already taken
            if store_check is None:  # if not taken
                store_school_qs = School.objects.filter(slug=store_school.strip())
                if not store_school_qs.exists():
                    raise GraphQLError("School does not exist, please try again")
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
                    vendor=profile,
                )  # create the store
                store.save()

                success = True

                user = User.objects.get(username=user.username)

                # return the vendor and user
                return CreateStoreMutation(success=success, user=user)
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
        if user.profile and not user.profile.store:
            user.profile.store.delete()
            return cls(success=False, user=user)
        else:
            return cls(success=True, user=user)


class UpdateStoreMutation(Output, graphene.Mutation):
    class Arguments:
        store_name = graphene.String()
        store_country = graphene.String()
        store_address = graphene.String()
        store_type = graphene.String()
        store_categories = graphene.List(graphene.String)
        store_phone_numbers = graphene.List(graphene.String)
        store_bio = graphene.String()
        store_nickname = graphene.String()
        store_school = graphene.String()
        store_cover_image = Upload()

    user = graphene.Field(UserNodeType)

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(
        self,
        info,
        store_name=None,
        store_country=None,
        store_address=None,
        store_type=None,
        store_categories=None,
        store_phone_numbers=None,
        store_bio=None,
        store_nickname=None,
        store_school=None,
        store_cover_image=None,
    ):
        success = False
        user = info.context.user
        profile = user.profile
        if profile.store is None:
            raise GraphQLError("You are not a vendor")
        store = Store.objects.filter(vendor=profile).first()
        if store is None:
            raise GraphQLError("You do not have a store")
        if store_name:
            store.store_name = store_name
        if store_country:
            store.store_country = store_country
        if store_address:
            store.store_address = store_address
        if store_type:
            store.store_type = store_type
        if store_categories:
            store.store_categories = store_categories
        if store_phone_numbers:
            store.store_phone_numbers = store_phone_numbers
        if store_bio:
            store.store_bio = store_bio
        if store_nickname:
            store.store_nickname = store_nickname
        if store_school:
            store_school_qs = School.objects.filter(slug=store_school.strip())
            if not store_school_qs.exists():
                raise GraphQLError("School does not exist, please try again")
            store.store_school = store_school_qs.first()
        if store_cover_image:
            store.store_cover_image = store_cover_image
        store.save()
        success = True

        return UpdateStoreMutation(success=success, user=user)

    @verification_required
    def resolve_mutation(cls, root, info, **kwargs):
        user = info.context.user
        if user.profile and user.profile.store:
            return cls(success=True, user=user)
        else:
            return cls(success=False, user=user)


class UpdateAccountMutation(UpdateAccountMixin, graphene.Mutation):
    class Arguments:
        first_name = graphene.String()
        last_name = graphene.String()
        email = graphene.String()
        phone_number = graphene.String()
        profile_image = Upload()
        country = graphene.String()
        state = graphene.String()
        city = graphene.String()

        is_student = graphene.Boolean()

    user = graphene.Field(UserNodeType)

    __doc__ = UpdateAccountMixin.__doc__

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(
        self,
        info,
        first_name=None,
        email=None,
        last_name=None,
        country=None,
        phone_number=None,
        profile_image=None,
        state=None,
        city=None,
    ):
        user = info.context.user
        send_email = False
        profile = Profile.objects.get(user__username=user.username)

        if first_name:
            user.first_name = first_name

        if last_name:
            user.last_name = last_name

        # update the profile values
        if country:
            profile.country = country

        if phone_number:
            profile.phone_number = phone_number

        if profile_image:
            profile.image = profile_image

        if city:
            profile.city = city

        if state:
            profile.state = state

        profile.save()

        if user.email != email:
            send_email = True
            user.status.verified = False

        if send_email == True:
            # try:
            user_status = UserStatus.objects.filter(user=user).first()
            user_status.clean_email(email)
            user.email = email
            user.save()
            user_status.send_activation_email(info)
            # except Exception as e:
            #     raise GraphQLError(
            #         "Error trying to send confirmation mail to %s" % email
            #     )
        user.save()
        user = User.objects.get(username=user.username)
        return UpdateAccountMutation(user=user)


class UpdateProfileMutation(Output, graphene.Mutation):
    class Arguments:
        gender = graphene.String()
        country = graphene.String()
        phone_number = graphene.String()
        state = graphene.String()
        city = graphene.String()
        is_student = graphene.String()
        school = graphene.String()
        campus = graphene.String()
        hostel = graphene.String()
        hostel_floor = graphene.String()
        hostel_room = graphene.String()

    user = graphene.Field(UserNodeType)

    @permission_checker([IsAuthenticated])
    def mutate(
        self,
        info,
        gender=None,
        country=None,
        phone_number=None,
        state=None,
        city=None,
        is_student=None,
        school=None,
        campus=None,
        hostel=None,
        hostel_floor=None,
        hostel_room=None,
    ):
        user = info.context.user
        profile = user.profile
        if profile is None:
            raise GraphQLError("Profile does not exist")

        if gender:
            gender = gender.upper().strip()
            gender = Gender.objects.filter(name=gender).first()

            if not profile.gender:
                gender.rank += 1
            else:
                gender.rank -= 1

            profile.gender = gender

            gender.save()

        if country:
            profile.country = country

        if phone_number:
            profile.phone_number = phone_number

        if state:
            profile.state = state

        if city:
            profile.city = city

        if is_student and is_student.lower().strip() == "yes":
            if profile.is_vendor:
                return GraphQLError("You are a vendor, you cannot be a student")

            student = Student.objects.get_or_create(user=profile)
            student = student[0]

            if school:
                school = School.objects.filter(slug=school.strip()).first()
                if not school:
                    raise GraphQLError("School does not exist")
                student.school = school
            if campus:
                student.campus = campus
            if hostel:
                hostel = Hostel.objects.filter(slug=hostel.strip()).first()
                if not hostel:
                    raise GraphQLError("Hostel does not exist")
                student.hostel = hostel
            if hostel_floor:
                student.floor = hostel_floor
            if hostel_room:
                student.room = hostel_room
            student.save()

        else:
            student = Student.objects.filter(user=profile)
            if student.exists():
                student = student.first()
                student.delete()
        profile.save()
        return UpdateProfileMutation(
            user=info.context.user, success=profile.has_required_fields
        )


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


class CreateTransferRecipient(Output, graphene.Mutation):
    class Arguments:
        account_number = graphene.String(required=True)
        account_name = graphene.String(required=True)
        bank_code = graphene.String(required=True)

    recipient_code = graphene.String()

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(self, info, account_number, account_name, bank_code):
        recipient_code = None
        success = False
        error = None
        user = info.context.user
        if user.role == "VENDOR":
            url = "https://api.paystack.co/transferrecipient"
            headers = {
                "Authorization": "Bearer " + PAYSTACK_SECRET_KEY,
                "Content-Type": "application/json",
            }
            data = {
                "type": "nuban",
                "name": account_name,
                "account_number": account_number,
                "bank_code": bank_code,
                "currency": "NGN",
            }

            response = requests.post(url, data=json.dumps(data), headers=headers)
            if response.status_code == 201:
                response = response.json()
                if response["status"] == True:
                    recipient_code = response["data"]["recipient_code"]
                    success = True
                else:
                    error = response["message"]
        else:  # the vendor does not exist
            error = "Vendor do not exist"
        return CreateTransferRecipient(
            success=success, error=error, recipient_code=recipient_code
        )


class WithdrawFromWalletMutation(Output, graphene.Mutation):
    class Arguments:
        amount = graphene.Float(required=True)
        recipient_code = graphene.String(required=True)
        account_name = graphene.String(required=True)
        pass_code = graphene.Int(required=True)
        reason = graphene.String(required=False)

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(
        self, info, amount, recipient_code, pass_code, account_name, reason=None
    ):
        user = info.context.user
        profile = user.profile
        error = None
        success = False
        wallet = Wallet.objects.filter(user=profile).first()

        # check if wallet exists
        if wallet is None:
            raise GraphQLError("Wallet does not exist, Please contact support")

        # check if passcode is empty
        if pass_code is None:
            raise GraphQLError("Pin cannot be empty")

        is_passcode = False
        try:
            is_passcode = wallet.check_passcode(pass_code)
        except Exception as e:
            raise GraphQLError(e)

        if is_passcode == False:
            raise GraphQLError("Wrong Pin")

        # check if the amount is greater than the balance
        transaction_fee = calculate_tranfer_fee(amount)
        if transaction_fee is None:
            raise GraphQLError("Invalid Amount")
        amount_with_charges = float(transaction_fee) + float(amount)

        if amount_with_charges > wallet.balance:
            raise GraphQLError("Insufficient Balance")

        # check if amount_with_charges is greater than the paystack balance
        paystack_balance = get_paystack_balance()
        if amount_with_charges > paystack_balance:
            user_wallet_balance = wallet.balance
            amount_able_to_tranfer = 0
            if user_wallet_balance > paystack_balance:
                amount_able_to_tranfer = paystack_balance - transaction_fee - 100
            else:
                amount_able_to_tranfer = user_wallet_balance - transaction_fee - 100

            if amount_able_to_tranfer < 0:
                amount_able_to_tranfer = 0

            raise GraphQLError(
                "Insufficient Balance, You can only withdraw "
                + str(amount_able_to_tranfer)
            )

        url = "https://api.paystack.co/transfer"
        headers = {
            "Authorization": "Bearer " + PAYSTACK_SECRET_KEY,
            "Content-Type": "application/json",
        }
        reference = str(uuid.uuid4())
        lower_amount = float(amount) * 100
        post_data = {
            "source": "balance",
            "amount": lower_amount,
            "reference": reference,
            "recipient": recipient_code,
            "reason": reason,
        }

        # create a transaction
        transaction = Transaction.objects.create(
            wallet=wallet,
            transaction_id=reference,
            transaction_fee=transaction_fee,
            title="Wallet Debited",
            status="pending",
            desc="TRF to " + account_name,
            amount=amount,
            _type="debit",
        )
        transaction.save()

        if not transaction is None:
            try:
                response = requests.post(
                    url, data=json.dumps(post_data), headers=headers
                )
                if response.status_code == 200:
                    response = response.json()
                    if not response["data"] or not response["data"]["status"]:
                        success = False
                        # delete the transaction
                        transaction.delete()
                        error = response["message"]
                    if response["status"] == True:
                        success = True
                    else:
                        success = False
                        # delete the transaction
                        transaction.delete()
                        error = response["message"]
                else:
                    success = False
                    # delete the transaction
                    transaction.delete()
                    error = response["message"]
            except Exception as e:
                success = False
                # delete the transaction
                transaction.delete()
                error = str(e)
        return WithdrawFromWalletMutation(success=success, error=error)


class ChangePinMutation(Output, graphene.Mutation):
    class Arguments:
        old_pin = graphene.Int(required=True)
        new_pin = graphene.Int(required=True)

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(self, info, old_pin, new_pin):
        user = info.context.user
        profile = user.profile
        error = None
        success = False
        wallet = Wallet.objects.filter(user=profile).first()

        new_pin = str(new_pin)
        old_pin = str(old_pin)

        # check if wallet exists
        if wallet is None:
            raise GraphQLError("Wallet does not exist, Please contact support")

        # check if old pin is empty
        if old_pin is None:
            raise GraphQLError("Old Pin cannot be empty")

        # check if new pin is empty
        if new_pin is None:
            raise GraphQLError("New Pin cannot be empty")

        is_old_pin = False
        try:
            is_old_pin = wallet.check_passcode(old_pin)
        except Exception as e:
            raise GraphQLError(e)

        if is_old_pin == False:
            raise GraphQLError("Wrong Old Pin")

        wallet.set_passcode(new_pin)
        wallet.save()

        success = True
        return ChangePinMutation(success=success, error=error)


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


class SendPhoneVerificationCodeMutation(Output, graphene.Mutation):
    class Arguments:
        country = graphene.String(
            required=True, description="Country code in ISO 3166-1 alpha-2 format"
        )
        phone = graphene.String(
            required=True, description="Phone number in E.164 format"
        )

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(self, info, phone, country):
        profile = info.context.user.profile
        success = False
        error = None

        from restcountries import RestCountryApiV2 as rapi

        get_country = rapi.get_country_by_country_code(country)

        # check if the country was found
        if get_country is None:
            raise GraphQLError(
                f"Issue with the country: '{country}', please contact support."
            )

        calling_code = get_country.calling_codes[0]

        if settings.DEBUG:
            success = True
            return SendPhoneVerificationCodeMutation(success=success, error=error)

        try:
            # send the verification code through twilio
            success = profile.send_phone_number_verification_code(
                new_phone_number=phone, calling_code=calling_code
            )
        except Exception as e:
            if "use" in str(e):
                error = "Phone number already in use, please try another."
            else:
                error = "Issue sending the OTP code, please try again."
            print(e)

        return SendPhoneVerificationCodeMutation(success=success, error=error)


class VerifyPhoneMutation(Output, graphene.Mutation):
    class Arguments:
        country = graphene.String(
            required=True, description="Country code in ISO 3166-1 alpha-2 format"
        )
        code = graphene.String(
            required=True,
            description="Verification code sent to the user's phone number",
        )

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(self, info, code, country):
        profile = info.context.user.profile
        success = False
        error = None

        from restcountries import RestCountryApiV2 as rapi

        get_country = rapi.get_country_by_country_code(country)

        # check if the country was found
        if get_country is None:
            raise GraphQLError(
                f"Issue with the country: '{country}', please contact support."
            )

        calling_code = get_country.calling_codes[0]

        if settings.DEBUG:
            success = True
            return VerifyPhoneMutation(success=success, error=error)

        try:
            # verify the phone number
            success = profile.verify_phone_number(code, calling_code)
        except Exception as e:
            error = "Incorrect OTP code, please try again."
            print(e)

        return VerifyPhoneMutation(success=success, error=error)


class AcceptDeliveryMutation(Output, graphene.Mutation):
    class Arguments:
        order_track_id = graphene.String(required=True)

    @permission_checker([IsAuthenticated])
    def mutate(self, info, order_track_id):
        user = info.context.user
        user_profile = user.profile
        delivery_person = user_profile.delivery_person

        if user.role != "DELIVERY_PERSON" or delivery_person is None:
            return AcceptDeliveryMutation(error="You are not a delivery personnal")

        order = Order.objects.filter(order_track_id=order_track_id).first()

        if order is None:
            return AcceptDeliveryMutation(error="This order Does not exists")

        if order.order_status == "cancelled" or order.order_payment_status == "failed":
            return AcceptDeliveryMutation(error="Order did not go through")

        if order.order_status == "delivered":
            return AcceptDeliveryMutation(error="Order is already delivered")

        if (
            order.delivery_person is None and order.order_payment_status == "success"
        ) or settings.DEBUG:
            order.delivery_person = delivery_person
            order.order_status = "shipped"
            # check if delivery person has more than 5 active orders
            active_orders_count = Order.objects.filter(
                delivery_person=delivery_person, order_status="shipped"
            ).count()
            if active_orders_count > 4:
                delivery_person.is_on_delivery = True
                delivery_person.save()
            order.save()
            return AcceptDeliveryMutation(success=True)
        else:
            return AcceptDeliveryMutation(error="This order was taken")


class UpdateStoreMenuMutation(Output, graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        action = graphene.String(required=True)

    @permission_checker([IsAuthenticated])
    def mutate(self, info, name, action):
        user = info.context.user
        user_profile = user.profile
        store = user_profile.store

        name = name.strip()

        if user.role != "VENDOR" or store is None:
            return UpdateStoreMenuMutation(error="You are not a vendor")

        # check if the name exists in the store menu json list
        exist_name = False

        name_in_lower_case = name.strip().lower()
        for menu in store.store_menu:
            menu = menu.strip().lower()
            if menu == name_in_lower_case:
                exist_name = True
                break

        if action == "add":
            if exist_name:
                return UpdateStoreMenuMutation(error="This menu already exists")
            store.store_menu.append(name)
            store.save()
            return UpdateStoreMenuMutation(success=True)
        elif action == "remove":
            # check of the name is 'all', then don't allow it
            if name_in_lower_case == "all":
                return UpdateStoreMenuMutation(error="You cannot remove 'all' menu")
            
            if not exist_name:
                return UpdateStoreMenuMutation(error="This menu does not exist")
            
            # check if store_products are already using the menu as store_menu_name
            store.store_products.filter(store_menu_name=name).update(store_menu_name="All")

            store.store_menu.remove(name)
            store.save()
            return UpdateStoreMenuMutation(success=True)
        else:
            return UpdateStoreMenuMutation(error="Invalid action")
