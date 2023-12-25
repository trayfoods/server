from celery import shared_task
from django.conf import settings
from trayapp.utils import get_twilio_client
from .models import UserDevice, UserAccount
from firebase_admin import messaging

TWILIO_CLIENT = get_twilio_client()


@shared_task
def graphql_auth_async_email(func, *args):
    """
    Task to send an e-mail for the graphql_auth package
    """

    return func(*args)


@shared_task
def send_async_sms(phone_number, message):
    """
    Task to send an SMS
    """
    try:
        TWILIO_CLIENT.messages.create(
            body=message, from_=settings.TWILIO_PHONE_NUMBER, to=phone_number
        )
    except Exception as e:
        print(e)


@shared_task
def send_fcm_notification_task(device_tokens):
    print("Sending notifications...")

    try:
        # Send a important notification to the devices corresponding to the provided
        message = messaging.MulticastMessage(
            tokens=device_tokens,
            data={
                "title": "Welcome To TrayFoods",
                "body": "Welcome to TrayFoods",
                "image": "https://trayfoods.com/icon-192x192.png",
                "click_action": "https://trayfoods.com/",
                "icon": "https://trayfoods.com/favicon.ico",
                "badge": "1",
                "sound": "default",
                "priority": "high",
                "content_available": True,
                "mutable_content": True,
                "android_channel_id": "trayfoods",
                "vibrate": "true",
                "visibility": "public",
                "importance": "high",
            },
        )

        # Send a message to the devices corresponding to the provided
        messaging.send_each_for_multicast(message)

    except Exception as e:
        print(f"Error sending notifications: {e}")
