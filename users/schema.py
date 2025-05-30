import graphene
from django.contrib.auth import get_user_model
from graphql_auth import mutations
from users.queries.transaction import TransactionQueries
from users.queries.wallet import WalletQueries
from users.queries.school import SchoolQueries
from users.queries.store import StoreQueries

from .mutations import (
    CreateUpdateStoreMutation,
    CreateTransferRecipient,
    WithdrawFromWalletMutation,
    ChangePinMutation,
    UpdatePersonalInfoMutation,
    CompleteProfileMutation,
    UserDeviceMutation,
    LoginMutation,
    RegisterMutation,
    SendPhoneVerificationCodeMutation,
    VerifyPhoneMutation,
    UpdateStoreMenuMutation,
    RearrangeStoreMenusMutation,
    UpdateSchoolInfoMutation,
    UpdateOnlineStatusMutation,
    HideWalletBalanceMutation,
    RequestAccountDeletionMutation,
    FindDeliveryPersonMutation,
)
from .models import Student
from .types import (
    StudentType,
    UserNodeType,
)
from graphql_auth.models import UserStatus
from django.conf import settings
from trayapp.custom_model import BankListQuery, EmailVerifiedNode

User = get_user_model()


class Query(
    BankListQuery,
    WalletQueries,
    StoreQueries,
    TransactionQueries,
    SchoolQueries,
    graphene.ObjectType,
):
    me = graphene.Field(UserNodeType)

    check_email_verification = graphene.Field(
        EmailVerifiedNode, email=graphene.String()
    )

    client = graphene.Field(StudentType, client_id=graphene.Int())

    def resolve_me(self, info):
        user = info.context.user
        if user.is_authenticated:
            return user
        return None

    def resolve_client(self, info, client_id):
        return Student.objects.get(pk=client_id)

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
                data["success"] = False if settings.USE_MAILERSEND else True
        else:  # the user does not exist
            data["msg"] = "email do not exists"
        return data


class AuthMutation(graphene.ObjectType):
    register = RegisterMutation.Field()
    verify_account = mutations.VerifyAccount.Field()
    resend_activation_email = mutations.ResendActivationEmail.Field()
    send_password_reset_email = mutations.SendPasswordResetEmail.Field()
    password_reset = mutations.PasswordReset.Field()
    password_change = mutations.PasswordChange.Field()
    request_account_deletion = RequestAccountDeletionMutation.Field()

    # django-graphql-jwt inheritances
    token_auth = LoginMutation.Field()
    verify_token = mutations.VerifyToken.Field()
    refresh_token = mutations.RefreshToken.Field()
    revoke_token = mutations.RevokeToken.Field()

    send_phone_verification_code = SendPhoneVerificationCodeMutation.Field()
    verify_phone = VerifyPhoneMutation.Field()


class Mutation(AuthMutation, graphene.ObjectType):
    update_personal_info = UpdatePersonalInfoMutation.Field()
    update_school_info = UpdateSchoolInfoMutation.Field()
    complete_profile = CompleteProfileMutation.Field()
    create_transfer_recipient = CreateTransferRecipient.Field()
    user_device = UserDeviceMutation.Field()
    withdraw_from_wallet = WithdrawFromWalletMutation.Field()
    hide_wallet_balance = HideWalletBalanceMutation.Field()
    change_pin = ChangePinMutation.Field()
    find_delivery_person = FindDeliveryPersonMutation.Field()

    create_update_store = CreateUpdateStoreMutation.Field()
    update_store_menu = UpdateStoreMenuMutation.Field()
    update_online_status = UpdateOnlineStatusMutation.Field()
    rearrange_store_menus = RearrangeStoreMenusMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
