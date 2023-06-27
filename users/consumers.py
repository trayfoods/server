from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from graphql_auth.models import UserStatus
import json

User = get_user_model()


class CheckEmailVerificationConsumer(AsyncWebsocketConsumer):
    async def websocket_connect(self, event):
        await self.accept()
        print("CONNECTED")

    async def websocket_disconnect(self, event):
        pass

    async def websocket_receive(self, event):
        text_data = event.get("text")
        if text_data:
            # Parse the incoming JSON message
            try:
                message = json.loads(text_data)
                email = message.get("email", "")
            except json.JSONDecodeError:
                await self.send_json_response(
                    {"success": False, "msg": "Invalid message format"}
                )
                return

            # Process the query
            response = await self.check_email_verification(email)

            # Send the response back to the client
            await self.send_json_response(response)

    async def send_json_response(self, data):
        await self.send(text_data=json.dumps(data))

    @database_sync_to_async
    def check_email_verification(self, email):
        data = {"success": False, "msg": None}
        user = User.objects.filter(email=email).first()
        if user is not None:
            user_status = UserStatus.objects.filter(user=user).first()
            if user_status and user_status.verified:
                data["success"] = True
            else:
                data["success"] = False
        else:
            data["msg"] = "Email does not exist"
        return data
