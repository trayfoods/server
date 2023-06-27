from channels.generic.websocket import JsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from graphql_auth.models import UserStatus

User = get_user_model()


class CheckEmailVerificationConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.accept()
        print("CONNECTED")

    def disconnect(self, close_code):
        pass

    def receive_json(self, content):
        email = content.get("email", "")

        # Process the query
        response = self.check_email_verification(email)

        # Send the response back to the client
        self.send_json(response)

    def send_json(self, data):
        self.send(data)

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
