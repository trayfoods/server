from celery import shared_task
from django.conf import settings
from trayapp.utils import get_twilio_client

TWILIO_CLIENT = get_twilio_client()


@shared_task
def graphql_auth_async_email(func, *args):
    """
    Task to send an e-mail for the graphql_auth package
    """

    return func(*args)


def send_async_sms(message, phone_number):
    """
    Task to send an SMS
    """
    try:
        TWILIO_CLIENT.messages.create(
            body=message, from_=settings.TWILIO_PHONE_NUMBER, to=phone_number
        )
    except Exception as e:
        print(e)
