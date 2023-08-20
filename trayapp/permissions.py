from graphql.error import GraphQLError


class BasePermission:
    @staticmethod
    def has_permission(context):
        return True


class IsAuthenticated(BasePermission):
    """
    permission to check for user authentication
    """

    @classmethod
    def has_permission(cls, context):
        return context.user and (
            context.user.is_authenticated and context.user.is_active
        )


def permission_checker(permissions: list):
    def wrap_decorator(func):
        def inner(cls, info, *args, **kwargs):
            if check_permission(permissions, info.context):
                return func(cls, info, **kwargs)

            raise GraphQLError("Permission Denied")

        return inner

    return wrap_decorator


def check_permission(permissions, context):
    return all(permission.has_permission(context) for permission in permissions)


from channels.db import database_sync_to_async
from graphql_jwt.shortcuts import get_user_by_token


class AuthenticationError(Exception):
    pass


def websocket_auth_required(func):
    """
    1. Extract the authentication token from the WebSocket headers
    2. Authenticate the user based on the token using the 'authenticate_user' function
    3. Set the user on the consumer instance
    4. Call the original WebSocket consumer method
    5. Handle exceptions or errors by closing the WebSocket connection
    """

    async def wrapper(self, message):
        print("message", "entered")
        try:
            # Extract the authentication token from the WebSocket headers
            token = (
                message.get("headers", {})
                .get("sec-websocket-protocol", "")
                .split(" ")[-1]
            )
            if not token:
                raise AuthenticationError("Token is missing")

            # Authenticate the user based on the token
            user = await authenticate_user(token)

            # Set the user on the consumer instance
            self.user = user

            # Call the original WebSocket consumer method
            return await func(self, message)
        except AuthenticationError as e:
            # Handle exceptions or errors
            await self.close()

    return wrapper


@database_sync_to_async
def authenticate_user(token):
    # Use the appropriate method to authenticate the user based on the token
    user = get_user_by_token(token)
    return user


from functools import wraps
from getpass import getpass
from django.core.management.base import CommandError
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings


def superuser_and_admin_required(email_subject):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **options):
            # Prompt for username and password
            username = input("Username: ")
            password = getpass("Password: ")

            # Authenticate the user
            user = authenticate(username=username, password=password)
            if user is None:
                raise CommandError("Invalid username or password.")

            # Check if the user is a superuser
            if not user.is_superuser:
                raise CommandError("You must be a superuser to execute this command.")

            # Check if the user is an admin
            if not user.is_staff:
                raise CommandError("You must be an admin to execute this command.")

            # Set the authenticated user to the command object
            self.user = user

            try:
                # Send email notification to the admin
                admin_email = (
                    settings.ADMIN_EMAIL
                )  # Replace with your admin email address
                message = f"User '{user.username}' has logged in to the '{email_subject}' command."
                send_mail(
                    email_subject, message, settings.DEFAULT_FROM_EMAIL, [admin_email]
                )
            except:
                pass

            # Execute the command function
            return func(self, *args, **options)

        return wrapper

    return decorator
