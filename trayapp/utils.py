import os
import requests
# Imaging and Filing
from pathlib import Path
from io import BytesIO
from PIL import Image
from django.core.files import File
# import blurhash
from pathlib import Path
from dotenv import load_dotenv


# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
load_dotenv(BASE_DIR / '.env')

image_types = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "gif": "GIF",
    "tif": "TIFF",
    "tiff": "TIFF",
}


def image_resize(image, width, height):
    # Open the image using Pillow
    img = Image.open(image)
    # check if either the width or height is greater than the max
    if img.width > width or img.height > height:
        output_size = (width, height)
        # Create a new resized “thumbnail” version of the image with Pillow
        img.thumbnail(output_size)
        # Find the file name of the image
        img_filename = Path(image.file.name).name
        # Spilt the filename on “.” to get the file extension only
        img_suffix = Path(image.file.name).name.split(".")[-1]
        # Use the file extension to determine the file type from the image_types dictionary
        img_format = image_types[img_suffix]
        # Save the resized image into the buffer, noting the correct file type
        buffer = BytesIO()
        img.save(buffer, format=img_format)
        # Wrap the buffer in File object
        file_object = File(buffer)
        # Save the new resized file as usual, which will save to S3 using django-storages
        image.save(img_filename, file_object)
        # if hash:
        #     hash = blurhash.encode(image, x_components=4, y_components=3)


def delete_dir(empty_dir):
    """path could either be relative or absolute. """
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
    if data['use_cursor']:
        reqUrl = 'https://api.paystack.co/bank?perPage={}&page={}&currency={}'.format(
            data['perPage'], data['page'], data['currency'])
    else:
        reqUrl = 'https://api.paystack.co/bank?currency={}'.format(
            data['currency'])
    r = requests.get(reqUrl, headers={
        "Authorization": "Bearer {}".format(PAYSTACK_SECRET_KEY)
    })
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
    reqUrl = 'https://api.paystack.co/bank/resolve?account_number={}&bank_code={}'.format(
        data['account_number'], data['bank_code'])
    r = requests.get(reqUrl, headers={
        "Authorization": "Bearer {}".format(PAYSTACK_SECRET_KEY)
    })
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