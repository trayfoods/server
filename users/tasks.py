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

    # try:
    message = messaging.MulticastMessage(
        tokens=device_tokens,
        data={"title": "Welcome To TrayFoods", "body": "Welcome to TrayFoods"},
        android=messaging.AndroidConfig(
            notification=messaging.AndroidNotification(
                title="Welcome To TrayFoods",
                body="Welcome to TrayFoods",
                image="https://trayfoods.com/logo.png",
            )
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title="Welcome To TrayFoods",
                        body="Welcome to TrayFoods",
                    ),
                    badge=1,
                    sound="default",
                )
            )
        ),
        webpush=messaging.WebpushConfig(
            notification=messaging.WebpushNotification(
                title="Welcome To TrayFoods",
                body="Welcome to TrayFoods",
                icon="https://trayfoods.com/logo.png",
            )
        ),
        # notification=messaging.Notification(
        #     title="Welcome To TrayFoods",
        #     body="Welcome to TrayFoods",
        #     image="https://trayfoods.com/logo.png",
        # ),
    )

    response = messaging.send_each_for_multicast(message)
    print(f"Successfully sent notifications: {response.success_count}")
    print(f"Failed notifications: {response.failure_count}")
    # except Exception as e:
    #     print(f"Error sending notifications: {e}")
