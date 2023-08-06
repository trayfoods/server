import os
import uuid
from django.db import models
from django.template.defaultfilters import slugify
from django.utils.translation import gettext_lazy as _
from django.conf import settings

import requests

User = settings.AUTH_USER_MODEL
FRONTEND_URL = settings.FRONTEND_URL
MEDIA_URL = settings.MEDIA_URL

PRODUCT_TYPES = (("TYPE", "TYPE"), ("CATEGORY", "CATEGORY"))

# profanity filter
from better_profanity import profanity


def filter_comment(comment):
    # better-profanity
    if profanity.contains_profanity(comment):
        comment = profanity.censor(comment)

    return comment


def item_directory_path(instance, filename):
    """
    Create a directory path to upload the Product's Image.
    :param object instance:
        The instance where the current file is being attached.
    :param str filename:
        The filename that was originally given to the file.
        This may not be taken into account when determining
        the final destination path.
    :result str: Directory path.file_extension.
    """
    item_name = slugify(instance.product.product_name)
    item_slug = slugify(instance.product.product_slug)
    _, extension = os.path.splitext(filename)
    return f"images/items/{item_slug}/{item_name}{extension}"


class ItemImage(models.Model):
    product = models.ForeignKey("Item", on_delete=models.CASCADE)
    item_image = models.ImageField(
        "Item Image",
        upload_to=item_directory_path,  # callback function
        null=False,
        blank=False,
        help_text=_("Upload Item Image."),
    )
    item_image_webp = models.ImageField(
        "Webp Item Image",
        upload_to=item_directory_path,
        null=True,
        blank=True,
        help_text=_("Upload Item Image In Webp Format."),
    )
    item_image_hash = models.CharField(
        "Item Image Hash", editable=False, max_length=32, null=True, blank=True
    )
    is_primary = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "-timestamp"]

    def __str__(self) -> str:
        return self.product.product_slug


class Item(models.Model):
    product_name = models.CharField(max_length=200)
    product_qty = models.IntegerField(default=0)
    product_price = models.FloatField()
    product_calories = models.IntegerField(default=0)
    product_desc = models.CharField(max_length=500, blank=True, null=True)
    product_share_visibility = models.CharField(
        max_length=20,
        choices=(("private", "private"), ("public", "public")),
        default="public",
        editable=False,
    )
    product_category = models.ForeignKey(
        "ItemAttribute",
        related_name="product_category",
        on_delete=models.SET_NULL,
        null=True,
    )

    product_type = models.ForeignKey(
        "ItemAttribute",
        related_name="product_type",
        on_delete=models.SET_NULL,
        null=True,
    )
    product_images = models.ManyToManyField(
        "ItemImage", related_name="product_image", blank=True, editable=False
    )
    product_avaliable_in = models.ManyToManyField(
        "users.Store", related_name="avaliable_in_store", blank=True
    )
    product_creator = models.ForeignKey(
        "users.Vendor", null=True, on_delete=models.SET_NULL, blank=True
    )
    product_created_on = models.DateTimeField(auto_now_add=True)
    product_clicks = models.IntegerField(default=0)
    product_views = models.IntegerField(default=0)
    product_slug = models.SlugField(null=False, unique=True)

    class Meta:
        ordering = ["-product_clicks"]

    def __str__(self):
        return self.product_name

    def save(self, *args, **kwargs):  # auto create product_slug
        if not self.product_slug:
            self.product_slug = slugify(self.product_name)
        return super().save(*args, **kwargs)

    # @property
    # def avaliable_store(self):
    #     return self.product_avaliable_in.first()

    @property
    def total_ratings(self):
        return self.ratings.count()

    @property
    def average_rating(self):
        ratings = self.ratings.all()
        count = ratings.count()
        if count > 0:
            sum_up = sum(rating.stars for rating in ratings)
            total = sum_up / count
            rounded_up = round(total * 10**1) / (10**1)
            return rounded_up
        return 0.0

    @property
    # check if the current user is the creator of the product
    def is_creator(self):
        return self.product_creator == self.request.user


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ratings")
    stars = models.IntegerField()
    comment = models.TextField(max_length=300, null=True, blank=True)
    users_liked = models.ManyToManyField(
        User, related_name="users_liked", blank=True, editable=False
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="ratings")
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "item")
        index_together = ("user", "item")
        ordering = ["-updated_on"]

    def __str__(self):
        return f"{self.user.username} - {self.item.product_name}"

    def save(self, *args, **kwargs):
        self.comment = filter_comment(self.comment)
        super().save(*args, **kwargs)


class ItemAttribute(models.Model):
    name = models.CharField(max_length=50)
    urlParamName = models.SlugField(null=False, unique=True)
    _type = models.CharField(max_length=10, choices=PRODUCT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):  # auto create urlParamName
        if not self.urlParamName:
            self.urlParamName = slugify(self.urlParamName)
        return super().save(*args, **kwargs)


class Order(models.Model):
    order_track_id = models.CharField(
        max_length=17,
        unique=True,
        editable=False,
    )
    order_status = models.CharField(
        max_length=20,
        choices=(
            ("not-started", "not-started"),
            ("processing", "processing"),
            ("delivered", "delivered"),
            ("cancelled", "cancelled"),
        ),
        default="not-started",
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    overall_price = models.FloatField(default=0.0, editable=False)
    delivery_price = models.FloatField(default=0.0, editable=False)
    shipping = models.JSONField(default=dict)
    stores_infos = models.JSONField(default=dict)
    linked_items = models.ManyToManyField(Item, editable=False)
    linked_stores = models.ManyToManyField("users.Store", editable=False)

    order_payment_currency = models.CharField(max_length=20, default="NGN")
    order_payment_method = models.CharField(max_length=20, default="card")
    order_payment_url = models.CharField(max_length=200, editable=False, blank=True)
    order_payment_status = models.CharField(
        max_length=20,
        editable=False,
        blank=True,
        null=True,
        choices=(("failed", "failed"), ("success", "success"), ("pending", "pending")),
    )
    delivery_person = models.ForeignKey(
        "users.DeliveryPerson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
    )
    order_message = models.TextField(blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.order_track_id:
            # Generate a custom ID if it doesn't exist
            self.order_track_id = "order_" + str(uuid.uuid4().hex)[:10]
        super().save(*args, **kwargs)

    def __str__(self):
        return "Order #" + str(self.order_track_id)

    # check if a store is linked in any order, if yes, return the orders
    @classmethod
    def get_orders_by_store(cls, store):
        return cls.objects.filter(linked_stores=store)

    # re-generate a order_track_id for the order and update the order_track_id of the order
    @property
    def regenerate_order_track_id(self):
        self.order_track_id = "order_" + str(uuid.uuid4().hex)[:10]
        self.save()
        return self.order_track_id

    @property
    def create_payment_link(self):
        PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY

        url = "https://api.paystack.co/transaction/initialize"

        # check if order has been initialized before
        if self.order_payment_status == "pending":
            order_track_id = self.regenerate_order_track_id
        else:
            order_track_id = self.order_track_id
        amount = self.overall_price
        amount = amount * 100

        callback_url = f"{FRONTEND_URL}/checkout/{order_track_id}"
        data = {
            "email": self.user.email,
            "currency": self.order_payment_currency,
            "amount": float(amount),
            "reference": f"{order_track_id}",
        }

        if "://" in FRONTEND_URL:
            data["callback_url"] = callback_url

        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        }

        response = requests.post(url, data=data, headers=headers)
        response = response.json()

        if response["status"] == True:
            transaction_id = response["data"]["reference"]
            payment_url = response["data"]["authorization_url"]
            self.order_payment_url = payment_url
            self.order_track_id = transaction_id
            self.order_payment_status = "pending"
            self.save()

        return response
