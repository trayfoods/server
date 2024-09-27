import requests
import json
import logging
import graphene
from graphql import GraphQLError
from graphene_file_upload.scalars import Upload
from django.utils.module_loading import import_string

from graphql_auth.models import UserStatus
from trayapp.utils import calculate_tranfer_fee
from users.mixins import RegisterMixin, ObtainJSONWebTokenMixin
from trayapp.permissions import IsAuthenticated, permission_checker

from .types import UserNodeType, StoreOpenHoursInput, AveragePreparationTimeInput
from product.types import MenuInputType
from .models import (
    Transaction,
    Store,
    StoreOpenHours,
    School,
    Student,
    Hostel,
    Gender,
    UserAccount,
    Wallet,
    DeliveryPerson,
    Profile,
    Menu,
)
from .inputs import StudentHostelFieldInput
from product.models import Order, ItemAttribute
from django.conf import settings
from core.utils import get_paystack_balance
import uuid

User = UserAccount
PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY

# get email_async_task from the graphql_auth settings

EMAIL_ASYNC_TASK = settings.GRAPHQL_AUTH.get("EMAIL_ASYNC_TASK", None)

if EMAIL_ASYNC_TASK and isinstance(EMAIL_ASYNC_TASK, str):
    async_email_func = import_string(EMAIL_ASYNC_TASK)
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
    unarchiving = graphene.Boolean(default_value=False)

    @classmethod
    def Field(cls, *args, **kwargs):
        cls._meta.arguments.update({"password": graphene.String(required=True)})
        for field in app_settings.LOGIN_ALLOWED_FIELDS:
            cls._meta.arguments.update({field: graphene.String()})
        return super(graphql_jwt.JSONWebTokenMutation, cls).Field(*args, **kwargs)


class UpdateOnlineStatusMutation(Output, graphene.Mutation):
    class Arguments:
        role = graphene.String(required=True)
        is_online = graphene.Boolean(required=True)

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(self, info, is_online: bool, role: str):
        user = info.context.user
        roles = user.roles
        allowed_roles = ["DELIVERY_PERSON", "VENDOR"]
        if not role in allowed_roles:
            return UpdateOnlineStatusMutation(error="Invalid role")

        if "DELIVERY_PERSON" == role:
            # check if the user is a delivery person
            if not "DELIVERY_PERSON" in roles:
                return UpdateOnlineStatusMutation(error="You are not a delivery person")
            delivery_person: DeliveryPerson = user.profile.get_delivery_person()
            if delivery_person.status == "suspended":
                delivery_person.status = "offline"
                delivery_person.save()
                return UpdateOnlineStatusMutation(
                    error="Your Delivery Account has been suspended, please contact support"
                )
            delivery_person.status = "online" if is_online else "offline"
            delivery_person.save()

        elif "VENDOR" == role:
            # check if the user is a vendor
            if not "VENDOR" in roles:
                return UpdateOnlineStatusMutation(error="You are not a vendor")
            store: Store = user.profile.store
            if store.status == "suspended":
                store.status = "offline"
                store.save()
                return UpdateOnlineStatusMutation(
                    error="Your Store has been suspended, please contact support"
                )
            store.status = "online" if is_online else "offline"
            store.save()
        return UpdateOnlineStatusMutation(success=True)


class CreateUpdateStoreMutation(Output, graphene.Mutation):
    class Arguments:
        event_type = graphene.String(required=True)
        # store details
        store_name = graphene.String()
        store_nickname = graphene.String()
        store_type = graphene.String()
        store_categories = graphene.List(graphene.String)
        store_bio = graphene.String()
        store_cover_image = Upload()
        has_physical_store = graphene.Boolean()
        gender_preference = graphene.String()

        # store location
        country = graphene.String()
        # if you are not a student that is creating a store, then you must provide the state, city, street_name, primary_address_lat, primary_address_lng
        state = graphene.String()
        city = graphene.String()
        primary_address = graphene.String()
        street_name = graphene.String()
        primary_address_lat = graphene.Float()
        primary_address_lng = graphene.Float()
        school = graphene.String()
        campus = graphene.String()

        timezone = graphene.String()

        # store contact
        whatsapp_numbers = graphene.List(graphene.String)
        instagram_handle = graphene.String()
        twitter_handle = graphene.String()
        facebook_handle = graphene.String()

        store_open_hours = graphene.List(StoreOpenHoursInput)
        store_average_preparation_time = graphene.Argument(AveragePreparationTimeInput)

    user = graphene.Field(UserNodeType)

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(
        self,
        info,
        event_type,
        store_open_hours: list[StoreOpenHoursInput] = None,
        **kwargs,
    ):
        user = info.context.user

        allowed_event_types = ["CREATE", "UPDATE"]

        required_fields = [
            "store_name",
            "store_nickname",
            "store_type",
            "store_categories",
            "store_cover_image",
            "has_physical_store",
            "country",
            "store_average_preparation_time",
        ]
        address_fields = [
            "state",
            "city",
            "primary_address",
            "street_name",
            "primary_address_lat",
            "primary_address_lng",
        ]
        if (
            "primary_address" in kwargs
            or "primary_address_lat" in kwargs
            or "primary_address_lng" in kwargs
        ):
            # add state, city, street_name, primary_address_lat, primary_address_lng to the required fields
            required_fields.extend(address_fields)
        if not event_type in allowed_event_types:
            return CreateUpdateStoreMutation(error="Invalid event type")

        # get kwargs values
        store_name = kwargs.get("store_name")
        store_nickname = kwargs.get("store_nickname")
        store_type = kwargs.get("store_type")
        store_categories = kwargs.get("store_categories")
        store_cover_image = kwargs.get("store_cover_image")
        store_bio = kwargs.get("store_bio")
        has_physical_store = kwargs.get("has_physical_store", False)
        gender_preference = kwargs.get("gender_preference", None)
        store_average_preparation_time = kwargs.get(
            "store_average_preparation_time", None
        )
        country = kwargs.get("country")

        state = kwargs.get("state")
        city = kwargs.get("city")
        primary_address = kwargs.get("primary_address")
        street_name = kwargs.get("street_name")
        primary_address_lat = kwargs.get("primary_address_lat")
        primary_address_lng = kwargs.get("primary_address_lng")
        school = kwargs.get("school")
        campus = kwargs.get("campus")

        # check if user is a student
        is_user_student = user.profile.is_student
        if is_user_student:
            user_profile: Profile = user.profile
            state = user_profile.state
            city = user_profile.city
            primary_address = ""
            street_name = ""
            primary_address_lat = 0.0
            primary_address_lng = 0.0

            user_student_profile: Student = user_profile.student
            school = user_student_profile.school.slug
            campus = user_student_profile.campus

        timezone = kwargs.get("timezone")
        whatsapp_numbers = kwargs.get("whatsapp_numbers")
        instagram_handle = kwargs.get("instagram_handle")
        twitter_handle = kwargs.get("twitter_handle")
        facebook_handle = kwargs.get("facebook_handle")

        if event_type == "CREATE":
            if not store_open_hours:
                return CreateUpdateStoreMutation(
                    error="Store Open Hours is required, please try again"
                )
            # check if the required fields are valid
            for field in required_fields:
                if not field in kwargs:
                    if field in address_fields and (
                        kwargs[field] is None or kwargs[field] == ""
                    ):
                        return CreateUpdateStoreMutation(
                            error="Valid Address is required, please try again".format(
                                field
                            )
                        )
                    return CreateUpdateStoreMutation(
                        error="{} is required".format(field)
                    )
            # check if the user is a vendor
            if "VENDOR" in user.roles:
                return CreateUpdateStoreMutation(error="You already have a store")
            # check if the store nickname is already taken
            if Store.objects.filter(store_nickname=store_nickname.strip()).exists():
                return CreateUpdateStoreMutation(
                    error="Nickname already exists, please use a unique name"
                )
        else:
            # check if the user is a vendor
            if not "VENDOR" in user.roles:
                return CreateUpdateStoreMutation(error="You are not a vendor")
            # check if the store exists
            if not user.profile.store:
                return CreateUpdateStoreMutation(error="Store does not exist")
            # check if the store nickname is already taken
            if (
                store_nickname
                and Store.objects.filter(store_nickname=store_nickname.strip())
                .exclude(vendor=user.profile)
                .exists()
            ):
                return CreateUpdateStoreMutation(
                    error="Nickname already exists, please use a unique name"
                )

        school_qs = None

        if school:
            if not campus:
                return CreateUpdateStoreMutation(
                    error="Campus is required, please try again"
                )
            school_qs = School.objects.filter(slug=school.strip())
            if not school_qs.exists():
                return CreateUpdateStoreMutation(
                    error="School does not exist, please try again"
                )
            # check if the campus can be found in the school campuses list
            school_campuses = school_qs.first().campuses
            if not campus in school_campuses:
                return CreateUpdateStoreMutation(
                    error="Campus does not exist, please try again"
                )

        if event_type == "CREATE":
            store = Store.objects.create(
                vendor=user.profile,
                # store details
                store_name=store_name,
                store_nickname=store_nickname,
                store_type=store_type,
                store_categories=store_categories,
                store_cover_image=store_cover_image,
                store_bio=store_bio,
                has_physical_store=has_physical_store,
                gender_preference=gender_preference,
                store_average_preparation_time=store_average_preparation_time,
                # store location
                country=country,
                city=city,
                state=state,
                primary_address=primary_address,
                street_name=street_name,
                primary_address_lat=primary_address_lat,
                primary_address_lng=primary_address_lng,
                school=school_qs.first(),
                campus=campus,
                timezone=timezone,
                # store contact
                whatsapp_numbers=whatsapp_numbers,
                instagram_handle=instagram_handle,
                twitter_handle=twitter_handle,
                facebook_handle=facebook_handle,
            )
        else:
            store: Store = user.profile.store
            # update the store details
            if store_name:
                store.store_name = store_name
            if store_nickname:
                store.store_nickname = store_nickname
            if store_type:
                store.store_type = store_type
            if store_categories:
                store.store_categories = store_categories
            if store_cover_image:
                store.store_cover_image = store_cover_image
            if store_bio:
                store.store_bio = store_bio
            store.has_physical_store = has_physical_store
            store.gender_preference = gender_preference
            if store_average_preparation_time:
                store.store_average_preparation_time = store_average_preparation_time
            # update the store location
            if country:
                store.country = country
            if city:
                store.city = city
            if state:
                store.state = state
            if primary_address:
                store.primary_address = primary_address
            if street_name:
                store.street_name = street_name
            if primary_address_lat:
                store.primary_address_lat = primary_address_lat
            if primary_address_lng:
                store.primary_address_lng = primary_address_lng
            if school and school_qs.exists():
                store.school = school_qs.first()
            if campus:
                store.campus = campus
            if timezone:
                store.timezone = timezone
            # update the store contact
            if whatsapp_numbers:
                store.whatsapp_numbers = whatsapp_numbers
            if instagram_handle:
                store.instagram_handle = instagram_handle
            if twitter_handle:
                store.twitter_handle = twitter_handle
            if facebook_handle:
                store.facebook_handle = facebook_handle
        store.save()

        if store_open_hours:
            # delete all the store open hours
            store.store_open_hours.all().delete()
            try:
                # loop and create store open hours
                for store_open_hour in store_open_hours:
                    StoreOpenHours.objects.create(
                        store=store,
                        day=store_open_hour.day,
                        open_time=store_open_hour.open_time,
                        close_time=store_open_hour.close_time,
                    )
            except Exception as e:
                # delete the store if there is an error
                if event_type == "CREATE":
                    store.delete()
                return CreateUpdateStoreMutation(error=str(e))

        # get all admin users email and send them a plain text email
        # to verify the store
        if event_type == "CREATE":
            try:
                admin_users = User.objects.filter(is_superuser=True)
                for admin_user in admin_users:
                    if async_email_func:
                        async_email_func(
                            subject="New Store Created",
                            message="""A new store has been created, please verify it.
                                    Store Name: {}
                                    Store Nickname: {}
                                    Store Type: {}
                                    Store Country: {}
                                    Link to store: https://api.trayfoods.com/admin/users/store/{}/
                                    """.format(
                                store.store_name,
                                store.store_nickname,
                                store.store_type,
                                store.country.code,
                                store.pk,
                            ),
                            recipient_list=[admin_user.email],
                        )
                    else:
                        admin_user.email_user(
                            subject="New Store Created",
                            message="""A new store has been created, please verify it.
                                    Store Name: {}
                                    Store Nickname: {}
                                    Store Type: {}
                                    Store Country: {}
                                    Link to store: https://api.trayfoods.com/admin/users/store/{}/
                                    """.format(
                                store.store_name,
                                store.store_nickname,
                                store.store_type,
                                store.country.code,
                                store.pk,
                            ),
                        )
            except Exception as e:
                logging.exception("Error sending email to admin users: ", e)

        # return the vendor and user
        return CreateUpdateStoreMutation(success=True, user=info.context.user)


class UpdatePersonalInfoMutation(Output, graphene.Mutation):
    class Arguments:
        first_name = graphene.String()
        last_name = graphene.String()
        email = graphene.String()
        profile_image = Upload()
        country = graphene.String()
        state = graphene.String()
        city = graphene.String()
        primary_address = graphene.String()
        street_name = graphene.String()
        primary_address_lat = graphene.Float()
        primary_address_lng = graphene.Float()

    user = graphene.Field(UserNodeType)

    @permission_checker([IsAuthenticated])
    def mutate(
        self,
        info,
        **kwargs,
    ):
        first_name = kwargs.get("first_name")
        last_name = kwargs.get("last_name")
        email = kwargs.get("email")
        profile_image = kwargs.get("profile_image")
        country = kwargs.get("country")
        state = kwargs.get("state")
        city = kwargs.get("city")
        primary_address = kwargs.get("primary_address")
        street_name = kwargs.get("street_name")
        primary_address_lat = kwargs.get("primary_address_lat")
        primary_address_lng = kwargs.get("primary_address_lng")

        user: UserAccount = info.context.user
        profile: Profile = user.profile

        if first_name:
            user.first_name = first_name

        if last_name:
            user.last_name = last_name

        user.save()

        # update the profile values
        if country:
            profile.country = country

        if profile_image:
            profile.image = profile_image

        if city:
            profile.city = city

        if state:
            profile.state = state

        if primary_address:
            # check if the primary_address_lat and primary_address_lng and street_name are empty
            if not primary_address_lat or not primary_address_lng or not street_name:
                return UpdatePersonalInfoMutation(
                    error="Use another address, the address you entered is not valid, please try again"
                )

            profile.primary_address = primary_address
            profile.street_name = street_name
            profile.primary_address_lat = primary_address_lat
            profile.primary_address_lng = primary_address_lng

        profile.save()

        if email and user.email != email:
            user.status.verified = False
            try:
                user_status = UserStatus.objects.filter(user=user).first()
                user_status.clean_email(email)
                user.email = email
                user.save()
                user_status.send_activation_email(info)
            except Exception as e:
                return UpdatePersonalInfoMutation(
                    error="Error trying to send confirmation mail to %s" % email
                )

        return UpdatePersonalInfoMutation(success=True, user=info.context.user)


class UpdateSchoolInfoMutation(Output, graphene.Mutation):
    class Arguments:
        school = graphene.String()
        campus = graphene.String()
        hostel = graphene.String()
        hostel_fields = graphene.List(StudentHostelFieldInput)

    user = graphene.Field(UserNodeType, default_value=None)

    @permission_checker([IsAuthenticated])
    def mutate(
        self,
        info,
        school=None,
        campus=None,
        hostel=None,
        hostel_fields: list[StudentHostelFieldInput] = None,
    ):
        user = info.context.user

        if not "STUDENT" in user.roles:
            return UpdateSchoolInfoMutation(error="You are not a student")

        student: Student = user.profile.student

        if school:
            school = School.objects.filter(slug=school.strip()).first()
            if not school:
                return UpdateSchoolInfoMutation(error="School does not exist")
            student.school = school
        if campus:
            student.campus = campus
        if hostel:
            hostel = Hostel.objects.filter(slug=hostel.strip()).first()
            if not hostel:
                return UpdateSchoolInfoMutation(error="Hostel does not exist")
            student.hostel = hostel
        if hostel_fields:
            student.hostel_fields = hostel_fields
        student.save()
        return UpdateSchoolInfoMutation(user=info.context.user, success=True)


class CompleteProfileMutation(Output, graphene.Mutation):
    class Arguments:
        gender = graphene.String(required=True)
        country = graphene.String(required=True)
        phone_number = graphene.String(required=True)
        roles = graphene.List(graphene.String, required=True)
        state = graphene.String(required=True)
        city = graphene.String(required=True)
        primary_address = graphene.String(required=True)
        street_name = graphene.String(required=True)
        primary_address_lat = graphene.Float(required=True)
        primary_address_lng = graphene.Float(required=True)

        school = graphene.String()
        campus = graphene.String()
        hostel = graphene.String()
        hostel_fields = graphene.List(StudentHostelFieldInput)

    required_fields = graphene.Boolean()
    need_verification = graphene.Boolean()
    user = graphene.Field(UserNodeType, default_value=None)

    @permission_checker([IsAuthenticated])
    def mutate(
        self,
        info,
        gender,
        country,
        phone_number,
        state,
        city,
        primary_address,
        street_name,
        primary_address_lat,
        primary_address_lng,
        roles,
        school: str = None,
        campus: str = None,
        hostel: str = None,
        hostel_fields: list[StudentHostelFieldInput] = None,
    ):
        user = info.context.user
        profile: Profile = user.profile
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
            profile.state = state
            profile.city = city
            profile.primary_address = primary_address
            profile.street_name = street_name
            profile.primary_address_lat = primary_address_lat
            profile.primary_address_lng = primary_address_lng
            profile.country = country

        if phone_number:
            profile.phone_number = phone_number

        # check if the role includes "DELIVERY_PERSON", then create the delivery person instance or update it
        if "DELIVERY_PERSON" in roles:
            delivery_person = DeliveryPerson.objects.get_or_create(profile=profile)
            delivery_person = delivery_person[0]
            delivery_person.save()

        # check if the user is a student, then create the student instance or update it
        if "STUDENT" in roles:
            student = Student.objects.get_or_create(
                user=profile
            )  # create the student instance if it does not exist
            student = student[0]

            if school:
                if (
                    not campus
                    or not hostel
                    or not hostel_fields
                    or len(hostel_fields) < 1
                ):
                    raise GraphQLError("Campus, Hostel and Hostel Fields are required")

                # check if the school can be found in the database
                school_qs = School.objects.filter(slug=school.strip())
                if not school_qs.exists():
                    raise GraphQLError("School does not exist")

                # check if the hostel can be found in the database
                hostel_qs = Hostel.objects.filter(slug=hostel.strip())
                if not hostel_qs.exists():
                    raise GraphQLError("Hostel does not exist")

                hostel_first_qs: Hostel = hostel_qs.first()

                qs_hostel_fields = hostel_first_qs.hostel_fields.all()

                # check if the hostel fields can be found in the database
                for hostel_field in hostel_fields:
                    hostel_field_qs = qs_hostel_fields.filter(
                        id=hostel_field.field_id.strip()
                    )
                    if not hostel_field_qs.exists():
                        raise GraphQLError(
                            "{} is not a related field of {}".format(
                                hostel_field_qs, hostel_first_qs.name
                            )
                        )

                # check if the campus can be found in the database
                school_campuses = (
                    school_qs.first().campuses
                )  # jsonfield list ['campus1', 'campus2']
                if not campus in school_campuses:
                    raise GraphQLError("Campus does not exist")

                # save the student instance
                student.campus = campus
                student.hostel = hostel_first_qs
                student.hostel_fields = hostel_fields
                student.school = school_qs.first()
                student.save()

        profile.has_required_fields = True
        profile.save()
        return CompleteProfileMutation(
            success=True,
            user=info.context.user,
            need_verification="VENDOR" in roles or "DELIVERY_PERSON" in roles,
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
        if user.profile.wallet:
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
            error = "You do not have a wallet, please contact support if you have any issues"
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
        profile: Profile = user.profile
        error = None
        success = False
        wallet = profile.get_wallet()

        # check if wallet exists
        if wallet is None:
            raise GraphQLError("Please contact support to continue")

        # the minimum amount that can be withdrawn is 100
        if amount < 100:
            raise GraphQLError(
                "Minimum amount that can be withdrawn is 100 {}".format(wallet.currency)
            )

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
        transfer_fee = calculate_tranfer_fee(amount)
        if transfer_fee is None:
            raise GraphQLError("Invalid Amount")
        amount_with_charges = float(transfer_fee) + float(amount)

        if amount_with_charges > wallet.balance:
            raise GraphQLError("Insufficient Balance")

        # check if amount_with_charges is greater than the paystack balance
        paystack_balance = get_paystack_balance()
        if amount_with_charges > paystack_balance:
            user_wallet_balance = wallet.balance
            amount_able_to_tranfer = 0
            if user_wallet_balance > paystack_balance:
                amount_able_to_tranfer = paystack_balance - transfer_fee - 100
            else:
                amount_able_to_tranfer = user_wallet_balance - transfer_fee - 100

            if amount_able_to_tranfer < 0:
                amount_able_to_tranfer = 0

            raise GraphQLError(
                f"You can only transfer a maximum of {str(amount_able_to_tranfer)} {wallet.currency} at the moment"
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
            transfer_fee=transfer_fee,
            title="TRF to " + account_name,
            status="pending",
            desc="We are processing your transfer, please wait a moment",
            amount=amount,
            _type="debit",
        )
        transaction.save()

        if not transaction is None:
            try:
                response = requests.post(
                    url, data=json.dumps(post_data), headers=headers
                )
                response_json = response.json()
                if response.status_code == 200:
                    if response_json["status"] == True:
                        success = True
                    else:
                        success = False
                else:
                    success = False

                # delete the transaction
                if success == False:
                    transaction.delete()
                    error = (
                        response_json["message"]
                        if "message" in response_json
                        else "Unable to transfer at the moment, please try again later"
                    )
            except Exception as e:
                success = False
                # delete the transaction
                transaction.delete()
                error = str(e)
                logging.exception("error from paystack", error)
        return WithdrawFromWalletMutation(success=success, error=error)


class ChangePinMutation(Output, graphene.Mutation):
    class Arguments:
        old_pin = graphene.Int()
        pwd = graphene.String()
        new_pin = graphene.Int(required=True)

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(self, info, new_pin, old_pin=None, pwd=None):
        # check if pwd and old_pin is not empty
        if pwd is None and old_pin is None:
            return ChangePinMutation(error="Old Pin or Password cannot be empty")

        user = info.context.user
        profile = user.profile
        wallet = Wallet.objects.filter(user=profile).first()

        new_pin = str(new_pin)

        # check if wallet exists
        if wallet is None:
            return ChangePinMutation(
                error="Wallet does not exist, Please contact support or try again later"
            )

        # check if new pin is empty
        if new_pin is None:
            return ChangePinMutation(error="New Pin cannot be empty")

        if old_pin:
            old_pin = str(old_pin)
            is_old_pin = wallet.check_passcode(old_pin)

            if is_old_pin == False:
                return ChangePinMutation(error="Wrong Old Pin")

        if pwd:
            is_pwd = wallet.user.user.check_password(pwd)

            if is_pwd == False:
                return ChangePinMutation(error="Wrong Password")

        else:
            return ChangePinMutation(error="Old Pin or Password cannot be empty")

        wallet.set_passcode(new_pin)
        wallet.save()

        return ChangePinMutation(success=True)


class UserDeviceMutation(Output, graphene.Mutation):
    class Arguments:
        device_token = graphene.String(required=True)
        device_type = graphene.String(required=False)
        action = graphene.String(required=True)

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(self, info, device_token, action, device_type=None):
        # check if action is in the list of actions
        list_of_actions = ["add", "remove"]
        if not action in list_of_actions:
            raise GraphQLError("Invalid action")

        user = info.context.user
        user_devices = user.devices.all()

        # check if the device token and device type exists in the user devices
        device = user_devices.filter(device_token=device_token, device_type=device_type)
        if not device.exists() and action == "add":
            user.add_device(
                **{
                    "device_token": device_token,
                    "device_type": device_type,
                }
            )
            return UserDeviceMutation(success=True)
        elif action == "remove":
            if device.exists():
                device = device.first()
                device.delete()
                return UserDeviceMutation(success=True)
            else:
                return UserDeviceMutation(error="Device token does not exist")
        else:
            return UserDeviceMutation(error="Device token already exists")


class SendPhoneVerificationCodeMutation(Output, graphene.Mutation):
    class Arguments:
        country = graphene.String(
            required=True, description="Country code in ISO 3166-1 alpha-2 format"
        )
        phone = graphene.String(
            required=True, description="Phone number in E.164 format"
        )

    pin_id = graphene.String(default_value=None)

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(self, info, phone, country):
        profile: Profile = info.context.user.profile
        success = False
        error = None

        pin_id = None

        phone = phone.strip()
        phone = phone.replace(" ", "")

        profile.clean_phone_number(phone)

        calling_code = profile.calling_code

        COUNTRY_CALLING_CODES = settings.COUNTRY_CALLING_CODES
        country_code_in_dict: str | None = COUNTRY_CALLING_CODES.get(country, None)

        # check if we already have the country calling code
        if country_code_in_dict:
            calling_code = country_code_in_dict
        else:
            get_country = None
            try:
                from restcountries import RestCountryApiV2 as rapi

                get_country = rapi.get_country_by_country_code(country)
            except Exception as e:
                logging.exception("Error getting country calling code: ", e)

            # check if the country was found
            if get_country is None:
                raise GraphQLError(f"please contact support to continue")

            calling_code = get_country.calling_codes[0]

        phone = phone.replace(calling_code, "")

        if settings.DEBUG or not settings.SMS_ENABLED:
            return SendPhoneVerificationCodeMutation(success=True)

        try:
            # send the verification code through twilio
            response = profile.send_phone_number_verification_code(
                new_phone_number=phone, calling_code=calling_code
            )
            success = response["success"]
            pin_id = response["pin_id"]
        except Exception as e:
            if "use" in str(e):
                error = "Phone number already in use, please try another."
            else:
                error = "Issue sending the OTP, please try again."

            logging.exception("Error sending phone verification code: ", e)

        return SendPhoneVerificationCodeMutation(
            success=success, error=error, pin_id=pin_id
        )


class VerifyPhoneMutation(Output, graphene.Mutation):
    class Arguments:
        pin_id = graphene.String(
            required=True, description="Temporary ID for the verification code"
        )
        code = graphene.String(
            required=True,
            description="Verification code sent to the user's phone number",
        )

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(self, info, code, pin_id):
        profile: Profile = info.context.user.profile
        success = False
        error = None

        if settings.DEBUG:
            return VerifyPhoneMutation(success=True)

        try:
            # verify the phone number
            success = profile.verify_phone_number(pin=code, pin_id=pin_id)
        except Exception as e:
            error = "Incorrect OTP code, please try again."
            logging.exception("Error verifying phone number: ", e)

        return VerifyPhoneMutation(success=success, error=error)


class FindDeliveryPersonMutation(Output, graphene.Mutation):
    class Arguments:
        order_id = graphene.String(required=True)

    @permission_checker([IsAuthenticated])
    def mutate(self, info, order_id):
        user: UserAccount = info.context.user
        # check if the user is not a vendor
        if not "VENDOR" in user.roles:
            return FindDeliveryPersonMutation(error="You are not a vendor")

        # Check if the order exists
        order = Order.objects.filter(order_track_id=order_id).first()
        if not order:
            return FindDeliveryPersonMutation(error="Order does not exist")

        # check if the vendor's store is linked to the order
        store = user.profile.store
        if not order.linked_stores.filter(id=store.id).exists():
            return FindDeliveryPersonMutation(error="You are not linked to this order")

        # send delivery request
        delivery_requested = DeliveryPerson.send_delivery(order=order, store=store)

        if delivery_requested:
            # update store status to ready-for-delivery
            order.update_store_status(store.id, "ready-for-delivery")
            return FindDeliveryPersonMutation(success=True)
        else:
            return FindDeliveryPersonMutation(
                error="No delivery person found, please try again later"
            )


class UpdateStoreMenuMutation(Output, graphene.Mutation):
    class Arguments:
        old_menu_name = graphene.String()
        menu = graphene.Argument(MenuInputType, required=True)
        action = graphene.String(required=True)

    @permission_checker([IsAuthenticated])
    def mutate(self, info, menu: MenuInputType, action: str, old_menu_name=None):
        user = info.context.user
        user_profile = user.profile
        store: Store = user_profile.store

        if not "VENDOR" in user.roles or store is None:
            return UpdateStoreMenuMutation(error="You are not a vendor")

        allowed_actions = ["add", "remove", "edit"]

        if not action in allowed_actions:
            return UpdateStoreMenuMutation(error="Invalid action")

        # check if any of the menu already exists
        menu.name = menu.name.lower()
        is_menu_exist = Menu.objects.filter(name=menu.name, store=store).exists()

        menu.type = ItemAttribute.objects.filter(slug=menu.type, _type="TYPE").first()

        if menu.type is None:
            return UpdateStoreMenuMutation(error="Invalid menu type")

        if action == "add":
            if is_menu_exist:
                return UpdateStoreMenuMutation(error=f"'{menu.name}' already exists")

            new_menu = Menu.objects.create(
                name=menu.name.lower(), type=menu.type, store=store
            )
            new_menu.save()

        elif action == "remove":
            if not is_menu_exist:
                return UpdateStoreMenuMutation(error=f"'{menu.name}' does not exists")

            menu_to_remove = Menu.objects.filter(name=menu.name, store=store).first()

            if not menu_to_remove:
                return UpdateStoreMenuMutation(error=f"'{menu.name}' does not exists")

            # prevent store from deleting `others` menu
            if menu_to_remove.name == "others":
                return UpdateStoreMenuMutation(
                    error="You cannot delete the 'Others' menu"
                )

            # get all the items in the menu
            items = menu_to_remove.get_menu_items()
            # change all the items to the `others` menu
            for item in items:
                store_others_menu = store.menus().filter(name="others").first()
                if not store_others_menu:
                    # create the others menu if it does not exist
                    others_menu = Menu.objects.create(
                        name="others", type=menu.type, store=store
                    )
                    others_menu.save()

                item.product_menu = store.menus().filter(name="others").first()
                item.save()

            menu_to_remove.delete()

        elif action == "edit":
            if not old_menu_name:
                return UpdateStoreMenuMutation(error="Old menu name is required")

            if not Menu.objects.filter(name=old_menu_name, store=store).exists():
                return UpdateStoreMenuMutation(error=f"'{menu.name}' does not exists")

            old_menu = Menu.objects.filter(name=old_menu_name, store=store).first()
            if not old_menu:
                return UpdateStoreMenuMutation(
                    error=f"'{old_menu_name}' does not exists"
                )

            old_menu.name = menu.name
            old_menu.type = menu.type
            old_menu.save()

        # loop and rearrange the menu position
        menus = store.menus()
        for index, menu in enumerate(menus):
            menu.position = index
            menu.save()

        return UpdateStoreMenuMutation(success=True)


class RearrangeStoreMenusMutation(Output, graphene.Mutation):
    class Arguments:
        menu_order = graphene.List(graphene.String, required=True)

    @permission_checker([IsAuthenticated])
    def mutate(self, info, menu_order: list[str]):
        user = info.context.user
        user_profile = user.profile
        store: Store = user_profile.store

        if not "VENDOR" in user.roles or store is None:
            return RearrangeStoreMenusMutation(error="You are not a vendor")

        store_menus = store.menus()

        if len(menu_order) != store_menus.count():
            return RearrangeStoreMenusMutation(
                error="Menu order does not match the number of menus"
            )

        for index, menu_name in enumerate(menu_order):
            menu = store_menus.filter(name=menu_name).first()
            if not menu:
                return RearrangeStoreMenusMutation(
                    error=f"{menu_name.capitalize()} does not exist"
                )

            menu.position = index
            menu.save()

        return RearrangeStoreMenusMutation(success=True)


class HideWalletBalanceMutation(Output, graphene.Mutation):
    class Arguments:
        is_hidden = graphene.Boolean()

    @permission_checker([IsAuthenticated])
    def mutate(self, info, is_hidden):
        user = info.context.user
        user_wallet = user.profile.get_wallet()

        if not user_wallet:
            return HideWalletBalanceMutation(
                error="There is no wallet linked to this account"
            )

        user_wallet.hide_balance = is_hidden
        user_wallet.save()
        return HideWalletBalanceMutation(success=True)


class RequestAccountDeletionMutation(Output, graphene.Mutation):
    class Arguments:
        reason = graphene.String(required=True)
        password = graphene.String(required=True)
        device = graphene.String(required=False)

    @permission_checker([IsAuthenticated])
    # send admin email that user wants to delete account
    def mutate(self, info, reason, password, device=None):
        user: User = info.context.user
        if not user.check_password(password):
            return RequestAccountDeletionMutation(error="Password is incorrect")
        # send email to admin users@trayfoods.com
        try:
            from django.core.mail import send_mail

            send_mail(
                subject="User Account Deletion Request",
                message=f"{user.email} has requested to delete their account. Reason: {reason}, Device: {device}",
                from_email="Users Admin <users@trayfoods.com>",
                recipient_list=[
                    "dev@trayfoods.com",
                    "coo@trayfoods.com",
                    "divuzki@gmail.com",
                    "divine@trayfoods.com",
                ],
                fail_silently=False,
            )

            user_profile: Profile = user.profile
            # notify the user that the request has been sent
            user_profile.send_sms(
                message="Sorry to see you go, your account deletion request has been sent to the admin. Please wait for a response"
            )
            # send email to user
            if device and device == "ios":
                user_profile.send_email(
                    subject="Account Deletion Process Has Started",
                    from_email="Trayfoods Accounts <accounts@trayfoods.com>",
                    text_content="Your account deletion has started, if this was not you, please contact support before 24hrs support@trayfoods.com",
                )
            else:
                user_profile.send_email(
                    subject="Account Deletion Requested",
                    from_email="Trayfoods Accounts <accounts@trayfoods.com>",
                    text_content="Your account deletion request has been sent to the admin. Please wait for a response",
                )

            # deactivate the user
            user.is_active = False
            user.save()
            return RequestAccountDeletionMutation(success=True)

        except Exception as e:
            logging.exception(e)
            return RequestAccountDeletionMutation(
                error="Error sending email, please try again"
            )
