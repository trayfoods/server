from decimal import Decimal
import os
import PIL
import blurhash
import numpy
import requests

# Imaging and Filing
from pathlib import Path
import io
import sys

from PIL import Image

# import blurhash
from pathlib import Path
from dotenv import load_dotenv

from django.conf import settings

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY_LIVE")
load_dotenv(BASE_DIR / ".env")


def calculate_total_amount(item_price, currency="NGN"):

    if currency == "NGN":
        # Define the transaction fee percentage and fixed fee
        transaction_fee_percentage = 1.5 / 100  # 1.5%
        fixed_fee = 100  # N100

        # Calculate the transaction fee
        transaction_fee = item_price * transaction_fee_percentage + fixed_fee

        # Calculate the total amount
        total_amount = item_price + transaction_fee

        return total_amount
    else:
        raise Exception("Currency not supported")


def calculate_tranfer_fee(amount: int, currency="NGN") -> int:
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

        return transfer_fee
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
        "country": "NGN" # required
    }
    ```
    """
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
        "account_number": "0690000031", # required
        "bank_code": "044" # required
    }
    ```
    """
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


from django.core.paginator import Paginator


def paginate_queryset(queryset, page_size, page):
    paginator = Paginator(queryset, page_size)
    paginated_queryset = paginator.get_page(page)
    return paginated_queryset
