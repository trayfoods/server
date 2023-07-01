import os
import requests

# Imaging and Filing
from pathlib import Path
import io
import sys

from PIL import Image, ImageFilter

# import blurhash
from pathlib import Path
from dotenv import load_dotenv


# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
load_dotenv(BASE_DIR / ".env")

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
    imageTemporaryResized.save(file, _image.format)

    if format:
        # Using BICUBIC interpolation for high-quality resizing in the specified format
        imageTemporaryResized = imageTemporaryResized.resize((w, h), Image.BICUBIC)
        content_type = f"image/{format}"
        imageTemporaryResized.save(file, format)

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


from django.core.paginator import Paginator


def paginate_queryset(queryset, page_size, page):
    paginator = Paginator(queryset, page_size)
    paginated_queryset = paginator.get_page(page)
    return paginated_queryset
