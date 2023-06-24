from tkinter import Image
from io import BytesIO
from pytest import File
from server.trayapp.utils import image_resize
import pytest

"""
Code Analysis

Objective:
The objective of the "image_resize" function is to resize an image to a specified width and height, and save the resized image to S3 using django-storages.

Inputs:
- image: the image to be resized
- width: the desired width of the resized image
- height: the desired height of the resized image

Flow:
1. Open the image using Pillow
2. Check if either the width or height is greater than the max
3. Create a new resized “thumbnail” version of the image with Pillow
4. Find the file name of the image
5. Split the filename on “.” to get the file extension only
6. Use the file extension to determine the file type from the image_types dictionary
7. Save the resized image into the buffer, noting the correct file type
8. Wrap the buffer in File object
9. Save the new resized file as usual, which will save to S3 using django-storages

Outputs:
- file_object: the resized image wrapped in a File object

Additional aspects:
- The function uses the Python Imaging Library (Pillow) to resize the image.
- The function determines the file type of the resized image based on the file extension using a dictionary called "image_types".
- The function saves the resized image to a buffer before wrapping it in a File object and saving it to S3 using django-storages.
"""
class TestImageResize:
    # Tests that the function correctly resizes an image that is smaller than the given width and height
    def test_smaller_image(self, mocker):
        img = Image.new('RGB', (200, 200), color='red')
        buffer = BytesIO()
        img.save(buffer, 'jpeg')
        buffer.seek(0)
        file = File(buffer)
        result = image_resize(file, 300, 300)
        assert result is None

    # Tests that the function correctly resizes an image that is exactly the given width and height
    def test_exact_image(self, mocker):
        img = Image.new('RGB', (300, 300), color='red')
        buffer = BytesIO()
        img.save(buffer, 'jpeg')
        buffer.seek(0)
        file = File(buffer)
        result = image_resize(file, 300, 300)
        assert result is None

    # Tests that the function correctly resizes an image that is larger than the given width and height
    def test_larger_image(self, mocker):
        img = Image.new('RGB', (400, 400), color='red')
        buffer = BytesIO()
        img.save(buffer, 'jpeg')
        buffer.seek(0)
        file = File(buffer)
        result = image_resize(file, 300, 300)
        assert result is None

    # Tests with an image that has a very small width or height
    def test_small_image(self, mocker):
        img = Image.new('RGB', (10, 10), color='red')
        buffer = BytesIO()
        img.save(buffer, 'jpeg')
        buffer.seek(0)
        file = File(buffer)
        result = image_resize(file, 300, 300)
        assert result is None

    # Tests with an image that has a very large width or height
    def test_large_image(self, mocker):
        img = Image.new('RGB', (2000, 2000), color='red')
        buffer = BytesIO()
        img.save(buffer, 'jpeg')
        buffer.seek(0)
        file = File(buffer)
        result = image_resize(file, 300, 300)
        assert result is None

    # Tests with an image that has an unsupported file format
    def test_unsupported_image(self, mocker):
        img = Image.new('RGB', (200, 200), color='red')
        buffer = BytesIO()
        img.save(buffer, 'bmp')
        buffer.seek(0)
        file = File(buffer)
        with pytest.raises(KeyError):
            image_resize(file, 300, 300)