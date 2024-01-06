from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from graphql_jwt.utils import get_payload
from channels.db import database_sync_to_async


class AuthenticationError(Exception):
    pass


class LogHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(request.META.get("HTTP_X_AUTHORIZATION"))  # Debug logging
        return self.get_response(request)


class JwtTokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            try:
                headers = dict(scope["headers"])
                encoded_token = headers.get(b"sec-websocket-protocol", b"").decode()

                if not encoded_token:
                    raise AuthenticationError("Invalid token")

                # Decode the JWT token
                user_model = get_user_model()
                user = None
                payload = get_payload(encoded_token)
                try:
                    username = payload["username"]
                    user = await database_sync_to_async(user_model.objects.get)(
                        username=username
                    )
                except (user_model.DoesNotExist, KeyError):
                    raise AuthenticationError("Invalid token")

                scope["user"] = user

            except AuthenticationError as e:
                # Handle authentication error here
                response = {
                    "type": "websocket.close",
                    "code": 403,  # Forbidden
                    "reason": str(e),
                }
                await send(response)
                return

        return await super().__call__(scope, receive, send)
