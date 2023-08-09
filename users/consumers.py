from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from graphql_auth.models import UserStatus
from users.models import Wallet
from users.signals import balance_updated

User = get_user_model()


class WalletBalanceConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        print("CONNECTED")

        # Register the consumer to receive balance_updated signal
        self.group_name = "wallet_balance_group"  # Choose an appropriate group name
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        balance_updated.connect(self.balance_updated_handler, sender=Wallet)
        await self.accept()

    async def disconnect(self, close_code):
        print("DISCONNECTED")
        # Unregister the consumer from receiving the signal
        balance_updated.disconnect(self.balance_updated_handler, sender=Wallet)
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # print out the received message
    async def receive(self, text_data):
        print("RECEIVED", text_data)

    async def receive_json(self, content):
        try:
            response = await self.get_wallet_balance()

            print("RESPONSE", response)

            await self.send_json(response)
        except Exception as e:
            await self.send_json({"error": str(e)})

    @database_sync_to_async
    def get_wallet_balance(self):
        print("GETTING WALLET BALANCE")
        data = {"success": False, "msg": None, "balance": None}
        user = self.scope["user"]
        if user is not None:
            user_status = Wallet.objects.filter(user=user.profile).first()
            if user_status and user_status.verified:
                data["success"] = True
                data["balance"] = user_status.wallet_balance
            else:
                data["msg"] = "User is not verified"
        else:
            data["msg"] = "User not authenticated"
        return data

    async def balance_updated_handler(self, event, **kwargs):
        await self.send_json(
            {"type": "wallet_balance.update", "balance": event["balance"]}
        )


class CheckEmailVerificationConsumer(AsyncJsonWebsocketConsumer):
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
