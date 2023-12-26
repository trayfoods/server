import graphene
from graphql_auth.exceptions import (
    UserNotVerified,
    WrongUsage,
    EmailAlreadyInUse,
    InvalidCredentials,
)
from graphql_auth.constants import Messages
from django.db import transaction
from smtplib import SMTPException
from graphql_jwt.decorators import token_auth
from graphql_auth.models import UserStatus
from users.models import UserAccount
from graphql_auth.settings import graphql_auth_settings as app_settings
from graphql_auth.mixins import Output
from graphql_auth.forms import RegisterForm
from graphql_auth.shortcuts import get_user_to_login
from graphql_jwt.exceptions import JSONWebTokenError
from django.core.exceptions import ObjectDoesNotExist

from .types import UserNodeType


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


class ObtainJSONWebTokenMixin(Output):
    """
    Obtain JSON web token for given user.

    Allow to perform login with different fields,
    and secondary email if set. The fields are
    defined on settings.

    Not verified users can login by default. This
    can be changes on settings.

    If user is archived, make it unarchive and
    return `unarchiving=True` on output.
    """

    token = graphene.String(default_value="")
    refresh_token = graphene.String(default_value="")

    @classmethod
    def resolve(cls, root, info, **kwargs):
        unarchiving = kwargs.get("unarchiving", False)
        return cls(unarchiving=unarchiving)

    @classmethod
    def resolve_mutation(cls, root, info, **kwargs):
        if len(kwargs.items()) != 2:
            raise WrongUsage(
                "Must login with password and one of the following fields %s."
                % (app_settings.LOGIN_ALLOWED_FIELDS)
            )

        try:
            next_kwargs = None
            USERNAME_FIELD = UserAccount.USERNAME_FIELD
            unarchiving = False

            # extract USERNAME_FIELD to use in query
            if USERNAME_FIELD in kwargs:
                query_kwargs = {USERNAME_FIELD: kwargs[USERNAME_FIELD]}
                next_kwargs = kwargs
                password = kwargs.get("password")
            else:  # use what is left to query
                password = kwargs.pop("password")
                query_field, query_value = kwargs.popitem()
                query_kwargs = {query_field: query_value}

            user = get_user_to_login(**query_kwargs)

            if not next_kwargs:
                next_kwargs = {
                    "password": password,
                    USERNAME_FIELD: getattr(user, USERNAME_FIELD),
                }
            if user.status.archived is True:  # unarchive on login
                UserStatus.unarchive(user)
                unarchiving = True

            if user.status.verified or app_settings.ALLOW_LOGIN_NOT_VERIFIED:
                return cls.parent_resolve(
                    root, info, unarchiving=unarchiving, **next_kwargs
                )
            if user.check_password(password):
                raise UserNotVerified
            raise InvalidCredentials
        except (JSONWebTokenError, ObjectDoesNotExist, InvalidCredentials):
            return cls(success=False, errors=Messages.INVALID_CREDENTIALS)
        except UserNotVerified:
            return cls(success=False, errors=Messages.NOT_VERIFIED)
