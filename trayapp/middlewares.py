from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from graphql_jwt.utils import get_payload
from channels.db import database_sync_to_async

class AuthenticationError(Exception):
    pass

class JwtTokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            headers = dict(scope["headers"])
            encoded_token = headers.get(b"sec-websocket-protocol", b"").decode()

            # Decode the JWT token
            user_model = get_user_model()
            user = None
            payload = get_payload(encoded_token)
            try:
                username = payload["username"]
                user = await database_sync_to_async(user_model.objects.get)(username=username)
            except (user_model.DoesNotExist, KeyError):
                pass

            scope["user"] = user

        return await super().__call__(scope, receive, send)
