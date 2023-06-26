from channels.generic.websocket import AsyncConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from graphql_auth.models import UserStatus
import json

User = get_user_model()

class CheckEmailVerificationConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        print("connected", event)
        await self.send({
            'type': 'websocket.accept'
        })

    async def websocket_disconnect(self, event):
        pass

    async def websocket_receive(self, event):
        text_data = event.get('text')
        if text_data:
            # Parse the incoming JSON message
            try:
                message = json.loads(text_data)
                email = message.get('email', '')
            except json.JSONDecodeError:
                await self.send({
                    'type': 'websocket.send',
                    'text': json.dumps({"success": False, "msg": "Invalid message format"})
                })
                return

            # Process the query
            response = await self.check_email_verification(email)

            # Send the response back to the client
            await self.send({
                'type': 'websocket.send',
                'text': json.dumps(response)
            })

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
            data["msg"] = "email does not exist"
        return data
