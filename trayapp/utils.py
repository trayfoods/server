from decimal import Decimal
import os
import requests
import logging
from pathlib import Path
from dotenv import load_dotenv

from django.conf import settings
import json

# Azure Queue Storage
from azure.storage.queue import (
    QueueClient,
    BinaryBase64EncodePolicy,
    BinaryBase64DecodePolicy,
)
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.identity import DefaultAzureCredential


# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY_LIVE")
load_dotenv(BASE_DIR / ".env")


def calculate_payment_gateway_fee(amount: Decimal, currency: str = "NGN") -> Decimal:
    if currency == "NGN":
        # Define the transaction fee percentage and fixed fee
        transaction_fee_percentage = 0.015  # 1.5%
        fixed_fee = 100  # N100

        # Calculate the transaction fee
        gateway_fee = Decimal(amount) * Decimal(transaction_fee_percentage) + Decimal(
            fixed_fee
        )

        return gateway_fee

    else:
        raise Exception("Currency not supported")


def calculate_total_amount(item_price: Decimal, currency="NGN"):
    """
    Calculate the total amount to be paid by the customer
    ```python
    item_price = 1000
    currency = "NGN"
    total_amount = calculate_total_amount(item_price, currency)
    print(total_amount) # 1015
    ```
    """
    if currency == "NGN":
        gateway_fee = calculate_payment_gateway_fee(item_price, currency)

        # Calculate the total amount
        total_amount = item_price + gateway_fee

        return total_amount
    else:
        raise Exception("Currency not supported")


def calculate_tranfer_fee(amount: Decimal, currency="NGN") -> Decimal:
    """
    Calculate the transfer fee
    ```python
    amount = 1000
    currency = "NGN"
    transfer_fee = calculate_tranfer_fee(amount, currency)
    print(transfer_fee) # 10
    ```
    """
    # Remove commas and convert the amount to a float
    float_amount = Decimal(amount)

    if currency == "NGN":
        transfer_fee = 10

        # Calculate the payment gateway fee
        if float_amount >= 50_000:
            transfer_fee = 100
        elif float_amount >= 10_000:
            transfer_fee = 50
        elif float_amount > 5001:
            transfer_fee = 20

        return Decimal(transfer_fee)
    else:
        raise Exception("Currency not supported")


def image_exists(image_path):
    # Construct full image path
    full_image_path = os.path.join(settings.MEDIA_ROOT, image_path)
    return os.path.isfile(full_image_path)


IMAGE_TYPES = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "gif": "GIF",
    "tif": "TIFF",
    "tiff": "TIFF",
}


def image_resized(image, w, h, format=None):
    """
    Resize an image
    ```python
    image = request.FILES["image"]
    w = 200
    h = 200
    image_resized(image, w, h) # returns a tuple of (file, name, content_type, size)
    ```
    """

    import io
    import sys
    from PIL import Image

    name = image.name
    _image = Image.open(image)

    # Calculate the aspect ratio of the original image
    aspect_ratio = _image.width / _image.height

    # Calculate the new width and height while preserving the aspect ratio
    if _image.width > _image.height:
        h = int(w / aspect_ratio)
    else:
        w = int(h * aspect_ratio)

    # Using BICUBIC interpolation for high-quality resizing
    imageTemporaryResized = _image.resize((w, h), Image.BICUBIC)

    file = io.BytesIO()
    content_type = Image.MIME[_image.format]
    imageTemporaryResized.save(file, _image.format, optimize=True, quality=95)

    if format:
        # Using BICUBIC interpolation for high-quality resizing in the specified format
        imageTemporaryResized = imageTemporaryResized.resize((w, h), Image.BICUBIC)
        content_type = f"image/{format}"
        imageTemporaryResized.save(file, format, optimize=True, quality=95)

    file.seek(0)
    size = sys.getsizeof(file)
    return file, name, content_type, size


def delete_dir(empty_dir):
    """path could either be relative or absolute."""
    # check if file or directory exists
    path = Path(empty_dir)
    path.rmdir()


def get_banks_list(data):
    """
    Get List Of Banks
    ```python
    data = {
        "use_cursor": False, # optional
        "perPage": 50, # optional
        "page": 1, # optional
        "currency": "NGN"
    }

    banks = get_banks_list(data) # returns a list of banks from the paystack api
    print(banks)
    ```
    """
    if "currency" not in data:
        raise Exception("Currency is required")

    if data["use_cursor"]:
        reqUrl = "https://api.paystack.co/bank?perPage={}&page={}&currency={}".format(
            data["perPage"], data["page"], data["currency"]
        )
    else:
        reqUrl = "https://api.paystack.co/bank?currency={}".format(data["currency"])
    r = requests.get(
        reqUrl, headers={"Authorization": "Bearer {}".format(PAYSTACK_SECRET_KEY)}
    )
    # check status code for response received
    # success code - 200
    banks = r.json()
    return banks


def get_bank_account_details(data):
    """
    Get bank account details
    ```python
    data = {
        "account_number": "1234567890",
        "bank_code": "044"
    }

    bank_details = get_bank_account_details(data) # returns a dict of bank details from the paystack api
    print(bank_details)
    ```
    """
    if "account_number" not in data:
        raise Exception("Account number is required")
    if "bank_code" not in data:
        raise Exception("Bank code is required")

    reqUrl = (
        "https://api.paystack.co/bank/resolve?account_number={}&bank_code={}".format(
            data["account_number"], data["bank_code"]
        )
    )
    r = requests.get(
        reqUrl, headers={"Authorization": "Bearer {}".format(PAYSTACK_SECRET_KEY)}
    )
    # check status code for response received
    # success code - 200
    bank_details = r.json()
    return bank_details


def get_dataframe_from_qs(queryset):
    """
    Get a pandas dataframe from a queryset
    """
    import pandas as pd

    df = pd.DataFrame.from_records(queryset.values())
    return df


import datetime


def convert_time_to_ago(time: datetime.datetime):
    """
    Convert time to ago
    """
    from django.utils import timezone

    # get the time difference between now and the time the transaction was created
    time_difference = timezone.now() - time
    # get the time difference in seconds
    time_difference_in_seconds = time_difference.total_seconds()
    # get the time difference in minutes
    time_difference_in_minutes = time_difference_in_seconds / 60
    # get the time difference in hours
    time_difference_in_hours = time_difference_in_minutes / 60

    # get the time difference in days
    time_difference_in_days = time_difference_in_hours / 24

    # get the time difference in weeks
    time_difference_in_weeks = time_difference_in_days / 7

    # get the time difference in months
    time_difference_in_months = time_difference_in_weeks / 4

    # get the time difference in years
    time_difference_in_years = time_difference_in_months / 12

    # return the time difference in the appropriate format
    if time_difference_in_seconds < 60:
        return "just now"
    elif time_difference_in_minutes < 60:
        return str(int(time_difference_in_minutes)) + " minutes ago"
    elif time_difference_in_hours < 24:
        return str(int(time_difference_in_hours)) + " hours ago"
    elif time_difference_in_days < 7:
        # check if it was yesterday
        if time_difference_in_days < 2:
            return "yesterday"
        else:
            return str(int(time_difference_in_days)) + " days ago"

    elif time_difference_in_weeks < 4:
        return str(int(time_difference_in_weeks)) + " weeks ago"
    elif time_difference_in_months < 12:
        return str(int(time_difference_in_months)) + " months ago"
    else:
        return str(int(time_difference_in_years)) + " years ago"


def paginate_queryset(queryset, page_size, page):
    from django.core.paginator import Paginator

    # Paginate the queryset
    paginator = Paginator(queryset, page_size)
    paginated_queryset = paginator.get_page(page)
    return paginated_queryset


def get_twilio_client():
    from twilio.rest import Client

    # Your Account Sid and Auth Token from twilio.com/console
    # and set the environment variables. See http://twil.io/secure
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def chunked_queryset(queryset, chunk_size=10000):
    """
    Slice a queryset into chunks. This is useful to avoid memory issues when
    iterating through large querysets.
    Code adapted from https://djangosnippets.org/snippets/10599/
    """

    # If the queryset is empty, return None
    if not queryset.exists():
        return

    # Order the queryset by primary key (pk)
    queryset = queryset.order_by("pk")

    # Get a list of all primary keys in the queryset
    pks = queryset.values_list("pk", flat=True)

    # Start with the first primary key
    start_pk = pks[0]

    # Loop indefinitely
    while True:
        try:
            # Try to get the primary key that is 'chunk_size' positions ahead of the current start_pk
            end_pk = pks.filter(pk__gte=start_pk)[chunk_size]
        except IndexError:
            # If we get an IndexError, it means we've reached the end of the queryset, so we break the loop
            break

        # Yield a chunk of the queryset that includes all objects with a pk greater than or equal to start_pk and less than end_pk
        yield queryset.filter(pk__gte=start_pk, pk__lt=end_pk)

        # Move the start_pk to the end_pk for the next iteration
        start_pk = end_pk

    # Yield the last chunk of the queryset that includes all objects with a pk greater than or equal to the final start_pk
    yield queryset.filter(pk__gte=start_pk)


def send_notification_to_queue(message, queue_name):
    """
    Sends notification data to a specified Azure Queue Storage queue.

    Args:
        message (dict): Dictionary containing notification details.
        queue_name (str): Name of the Azure Queue Storage queue.
    """

    has_error = False

    try:
        # Create Queue Client (using DefaultAzureCredential for authentication)
        account_url = f"https://{settings.AZURE_ACCOUNT_NAME}.queue.core.windows.net"
        default_credential = DefaultAzureCredential()

        queue_client = QueueClient(
            account_url=account_url,
            queue_name=queue_name,
            credential=default_credential,
        )

        if not isinstance(message, dict):
            raise ValueError("message must be a dictionary.")

        # Setup Base64 encoding and decoding functions
        queue_client.message_encode_policy = BinaryBase64EncodePolicy()
        queue_client.message_decode_policy = BinaryBase64DecodePolicy()

        # Encode and send message to queue
        message_string = json.dumps(message)
        message_bytes = message_string.encode("utf-8")
        queue_client.send_message(
            queue_client.message_encode_policy.encode(content=message_bytes)
        )

    except Exception as e:
        has_error = True
        logging.error(f"Error sending message to queue: {e}")

    return has_error


def send_message_to_queue_bus(message_dict, queue_name, ttl=None):
    credential = DefaultAzureCredential()
    service_bus_client = ServiceBusClient(
        credential=credential,
        fully_qualified_namespace="trayfoods.servicebus.windows.net",
        queue_name=queue_name,
    )
    # convert the dictionary to a json string
    message_json = json.dumps(message_dict)
    message_obj = ServiceBusMessage(message_json)

    if ttl:
        message_obj.time_to_live = ttl

    with service_bus_client:
        sender = service_bus_client.get_queue_sender(queue_name)
        sender.send_messages(message_obj)
