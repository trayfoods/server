import graphene
from graphql_auth.exceptions import EmailAlreadyInUse
from graphql_auth.constants import Messages
from django.db import transaction
from smtplib import SMTPException
from graphql_jwt.decorators import token_auth
from graphql_auth.models import UserStatus
from users.models import UserAccount
from graphql_auth.settings import graphql_auth_settings as app_settings
from graphql_auth.mixins import Output
from graphql_auth.forms import RegisterForm

from .types import UserNodeType  # , BankNode


class RegisterMixin(Output):
    """
    Register user with fields defined in the settings.

    If the email field of the user model is part of the
    registration fields (default), check if there is
    no user with that email or as a secondary email.

    If it exists, it does not register the user,
    even if the email field is not defined as unique
    (default of the default django user model).

    When creating the user, it also creates a `UserStatus`
    related to that user, making it possible to track
    if the user is archived, verified and has a secondary
    email.

    Send account verification email.

    If allowed to not verified users login, return token.
    """

    form = RegisterForm

    token = graphene.String()
    refresh_token = graphene.String()
    user = graphene.Field(UserNodeType)

    @classmethod
    @token_auth
    def login_on_register(cls, root, info, **kwargs):
        return cls()

    @classmethod
    def resolve_mutation(cls, root, info, **kwargs):
        try:
            with transaction.atomic():
                f = cls.form(kwargs)
                if f.is_valid():
                    email = kwargs.get(UserAccount.EMAIL_FIELD, False)
                    UserStatus.clean_email(email)
                    user = f.save()
                    send_activation = (
                        app_settings.SEND_ACTIVATION_EMAIL is True and email
                    )
                    if send_activation:
                        user.status.send_activation_email(info)
                    if app_settings.ALLOW_LOGIN_NOT_VERIFIED:
                        payload = cls.login_on_register(
                            root, info, password=kwargs.get("password1"), **kwargs
                        )
                        payload.user = user
                        return_value = {}
                        for field in cls._meta.fields:
                            print(getattr(payload, field), field)
                            return_value[field] = getattr(payload, field)
                        return cls(**return_value)
                    return cls(success=True, user=user)
                else:
                    return cls(success=False, errors=f.errors.get_json_data())
        except EmailAlreadyInUse:
            return cls(
                success=False,
                # if the email was set as a secondary email,
                # the RegisterForm will not catch it,
                # so we need to run UserStatus.clean_email(email)
                errors={UserAccount.EMAIL_FIELD: Messages.EMAIL_IN_USE},
            )
        except SMTPException:
            return cls(success=False, errors=Messages.EMAIL_FAIL)
