from celery import shared_task
from django.conf import settings
from trayapp.utils import get_twilio_client
from django.core.management import call_command

TWILIO_CLIENT = get_twilio_client()


@shared_task
def settle_transactions():
    call_command("settle_transactions")


@shared_task
def graphql_auth_async_email(func, *args):
    """
    Task to send an e-mail for the graphql_auth package
    """

    return func(*args)


@shared_task
def send_async_sms(phone_number, message):
    print("send_async_sms", phone_number, message)
    """
    Task to send an SMS
    """
    # try:

    tw = TWILIO_CLIENT.messages.create(
        body=message, from_=settings.TWILIO_PHONE_NUMBER, to=phone_number
    )

    print(tw)
    # print out the message sid
    print(message.sid)
