from decimal import Decimal
import os
import uuid
from django.db import models
from django.template.defaultfilters import slugify
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from trayapp.utils import calculate_payment_gateway_fee

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
    product_name = models.CharField(max_length=100)
    product_qty = models.IntegerField(default=0)
    has_qty = models.BooleanField(default=False, editable=False)
    product_qty_unit = models.CharField(max_length=20, blank=True, null=True)
    product_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    product_calories = models.FloatField(default=0.0)
    product_desc = models.CharField(max_length=200, blank=True, null=True)
    product_share_visibility = models.CharField(
        max_length=20,
        choices=(("private", "private"), ("public", "public")),
        default="public",
        editable=False,
    )
    store_menu_name = models.CharField(
        max_length=30,
        default="OTHERS",
        blank=True,
    )

    product_categories = models.ManyToManyField(
        "ItemAttribute",
        related_name="product_categories",
        blank=True,
    )

    product_type = models.ForeignKey(
        "ItemAttribute",
        related_name="product_type",
        on_delete=models.SET_NULL,
        null=True,
    )
    product_creator = models.ForeignKey(
        "users.Store", null=True, on_delete=models.CASCADE, blank=True
    )
    product_created_on = models.DateTimeField(auto_now_add=True)
    product_clicks = models.IntegerField(default=0)
    product_views = models.IntegerField(default=0)
    product_slug = models.SlugField(null=False, unique=True)
    product_currency = models.CharField(max_length=20, default="NGN")

    product_status = models.CharField(
        max_length=20,
        choices=(
            ("active", "active"),
            ("inactive", "inactive"),
            ("deleted", "deleted"),
        ),
        default="active",
    )

    is_groupable = models.BooleanField(default=False)

    class Meta:
        ordering = ["-product_clicks"]

    def __str__(self):
        return self.product_name

    def save(self, *args, **kwargs):  # auto create product_slug
        if not self.product_slug:
            self.product_slug = slugify(self.product_name + "-" + str(uuid.uuid4().hex)[:6])

        if not self.product_creator:
            self.product_creator = self.request.user.profile.store

        if self.product_qty > 0:
            self.has_qty = True
        return super().save(*args, **kwargs)

    @property
    def product_images(self):
        return ItemImage.objects.filter(product=self)

    # exclude the item that is deleted from the objects
    @classmethod
    def get_items(cls):
        """
        eg: Item.get_items()
        """
        return (
            cls.objects.exclude(product_status="deleted")
            .exclude(product_creator__is_approved=False)
            .exclude(product_type__slug__icontains="package")
        )

    # filter the product available in a store
    @classmethod
    def get_items_by_store(cls, store):
        """
        eg: Item.get_items_by_store(store)
        """
        return cls.objects.exclude(product_status="deleted").filter(
            product_creator=store
        )

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
        return self.product_creator and (
            self.product_creator == self.request.user.profile.store
        )

    @property
    # get the creator of the product country
    def product_country(self):
        return self.product_creator and self.product_creator.user.country

    @property
    def is_avaliable_for_pickup(self):
        return self.is_avaliable and self.product_creator.has_physical_store

    @property
    def is_avaliable(self):
        if self.product_creator:
            if not self.product_creator.is_approved:
                return False
        return self.product_status == "active"


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
    slug = models.SlugField(null=False, unique=True)
    _type = models.CharField(max_length=10, choices=PRODUCT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):  # auto create slug
        if not self.slug:
            self.slug = slugify(self.slug)
        return super().save(*args, **kwargs)


ALLOWED_STORES_STATUS = settings.ALLOWED_ORDER_STATUS


class Order(models.Model):
    order_track_id = models.CharField(
        max_length=24,
        unique=True,
        editable=False,
    )
    order_status = models.CharField(
        max_length=26,
        choices=(
            ("not-started", "not-started"),
            ("processing", "processing"),
            ("partially-accepted", "partially-accepted"),
            ("accepted", "accepted"),
            ("partially-rejected", "partially-rejected"),
            ("rejected", "rejected"),
            ("partially-ready-for-pickup", "partially-ready-for-pickup"),
            ("ready-for-pickup", "ready-for-pickup"),
            ("partially-out-for-delivery", "partially-out-for-delivery"),
            ("out-for-delivery", "out-for-delivery"),
            ("partially-delivered", "partially-delivered"),
            ("delivered", "delivered"),
            ("partially-cancelled", "partially-cancelled"),
            ("cancelled", "cancelled"),
            ("failed", "failed"),
        ),
        default="not-started",
        db_index=True,
    )
    stores_status = models.JSONField(default=list, blank=True)
    # the stores_status json format is as follows
    # [{
    #     "storeId": store.id,
    #     "status": "processing",
    # }]

    user = models.ForeignKey("users.Profile", on_delete=models.CASCADE)

    overall_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0, editable=False
    )
    delivery_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0, editable=False
    )
    extra_delivery_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0, editable=False
    )
    service_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0, editable=False
    )
    shipping = models.JSONField(default=dict)
    stores_infos = models.JSONField(default=list)
    store_notes = models.JSONField(
        default=list,
        blank=True,
    )
    # the delivery people json format is as follows
    # [{
    #     "id": delivery_person,
    #     "status": "out-for-delivery",
    #     "storeId": store.id,
    # }]
    delivery_people = models.JSONField(default=list, blank=True)

    linked_items = models.ManyToManyField(Item, editable=False)
    linked_stores = models.ManyToManyField("users.Store", editable=False)
    linked_delivery_people = models.ManyToManyField(
        "users.DeliveryPerson", editable=False, related_name="linked_delivery_people"
    )

    order_currency = models.CharField(max_length=20, default="NGN")
    order_payment_method = models.CharField(max_length=20, default="card")
    order_payment_url = models.CharField(max_length=200, editable=False, blank=True)
    order_payment_status = models.CharField(
        max_length=25,
        editable=False,
        blank=True,
        null=True,
        choices=(
            ("failed", "failed"), 
            ("success", "success"),
              ("pending", "pending"),
                ("pending-refund", "pending-refund"), 
                 ("partially-refunded", "partially-refunded"),
                 ("refunded", "refunded"),
                 ("partially-failed-refund", "partially-failed-refund"),
                 ("failed-refund", "failed-refund"),
            ),
    )

    delivery_person_note = models.CharField(blank=True, null=True, max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order_confirm_pin = models.CharField(max_length=4, blank=True, null=True)
    activities_log = models.JSONField(default=list, blank=True)
    # the activities_log json format is as follows
    # [{
    #   "title": "Order Created",
    #   "description": "The order was created by the user",
    #   "timestamp": "2021-09-01 12:00:00"
    # }]

    class Meta:
        ordering = ["-created_at", "-updated_at"]

    def save(self, *args, **kwargs):
        if not self.order_track_id:
            # Generate a custom ID if it doesn't exist
            order_track_id = "order_" + str(uuid.uuid4().hex)[:10]
            while Order.objects.filter(order_track_id=order_track_id).exists():
                order_track_id = "order_" + str(uuid.uuid4().hex)[:17]
            self.order_track_id = order_track_id

        # check if all the delivery people are linked to the order, if not, then clear the linked_delivery_people and add the delivery people
        if self.id:
            # validate the stores_status format is correct
            if not self.validate_stores_status():
                raise ValueError("Invalid stores_status format")

            # validate the delivery people format is correct
            if not self.validate_delivery_people():
                raise ValueError("Invalid delivery people format")

            # validate the activities_log format is correct
            if not self.validate_activities_log():
                raise ValueError("Invalid activities log format")

            delivery_people = self.delivery_people
            if delivery_people:
                if len(delivery_people) > 0:
                    # check if all the delivery people are linked to the order
                    for delivery_person in delivery_people:
                        if not self.linked_delivery_people.filter(
                            id=delivery_person.get("id")
                        ).exists():
                            self.linked_delivery_people.clear()
                            break
                    # add the delivery people to the order
                    for delivery_person in delivery_people:
                        if not self.linked_delivery_people.filter(
                            id=delivery_person.get("id")
                        ).exists():
                            self.linked_delivery_people.add(delivery_person.get("id"))
                else:
                    self.linked_delivery_people.clear()

        super().save(*args, **kwargs)

    def __str__(self):
        return "Order #" + str(self.order_track_id)
    
    # get order display id
    def get_order_display_id(self):
        order_track_id = self.order_track_id
        formatteed_order_track_id = order_track_id.replace("order_", "")
        return f"#{formatteed_order_track_id}".upper()

    # validate the order store status format is correct
    def validate_stores_status(self):
        stores_status = self.stores_status
        if not isinstance(stores_status, list):
            return False
        if len(stores_status) == 0:
            return True

        for store_status in stores_status:
            if not store_status.get("storeId"):
                return False
            if not store_status.get("status"):
                return False
            if store_status.get("status") not in ALLOWED_STORES_STATUS:
                return False
            # check if the stores_status are linked to the order
            if not self.linked_stores.filter(id=store_status.get("storeId")).exists():
                return False
        # check of there is any duplicate store_status ["storeId"]
        stores_status_ids = [store_status["storeId"] for store_status in stores_status]
        if len(stores_status_ids) != len(set(stores_status_ids)):
            return False
        return True

    # validate the order delivery people format is correct
    def validate_delivery_people(self):
        delivery_people = self.delivery_people
        if not isinstance(delivery_people, list):
            return False
        if len(delivery_people) == 0:
            return True

        for delivery_person in delivery_people:
            if not delivery_person.get("id"):
                return False
            if not delivery_person.get("status"):
                return False
            if not delivery_person.get("storeId"):
                return False
            # check if the delivery people are linked to the order
            if not self.linked_delivery_people.filter(
                id=delivery_person.get("id")
            ).exists():
                return False
        # check of there is any duplicate delivery person ["id"]
        delivery_people_ids = [
            delivery_person["id"] for delivery_person in delivery_people
        ]
        if len(delivery_people_ids) != len(set(delivery_people_ids)):
            return False
        return True

    # validate the activities_log format is correct
    def validate_activities_log(self):
        activities_log = self.activities_log
        if not isinstance(activities_log, list):
            return False
        if len(activities_log) == 0:
            return True

        for activity in activities_log:
            if not activity.get("title"):
                return False
            if not activity.get("description"):
                return False
            if not activity.get("timestamp"):
                return False

        return True

    def get_confirm_pin(self):
        if not self.order_confirm_pin:
            self.order_confirm_pin = str(uuid.uuid4().hex)[:4]
            self.save()
        return self.order_confirm_pin


    def is_pickup(self):
        shipping = self.shipping
        return (
            shipping and shipping["address"] and shipping["address"].lower() == "pickup"
        )

    def notify_delivery_people(self, delivery_people, store_id):
        print("notify_delivery_people", delivery_people)
        shipping = self.shipping
        order_address = f"{shipping["address"]} {shipping["sch"]}"
        for delivery_person in delivery_people:
            has_sent_push_notification = delivery_person.profile.send_push_notification(
               title="New Order",
               msg="You have a new order to deliver, check your account page for more details.",
            )
            if not has_sent_push_notification:
                has_sent_sms = delivery_person.profile.send_sms(
                    "You have a new order to deliver.\nOrder ID: {}\nOrder Address: {}\nClick on the link below to accept the order.{}".format(
                        self.get_order_display_id(),
                        order_address,
                        f"{FRONTEND_URL}/order/{self.order_track_id}/accept-delivery",
                    )
                )
                if not has_sent_sms:
                    self.update_store_status(store_id, "no-delivery-person")
        return True
    
    def notify_user(self, message: str, title: str = "Order Status"):
        has_sent_push_notification = self.user.send_push_notification(
            title=title,
            msg=message,
        )
        if not has_sent_push_notification:
            has_sent_sms = self.user.send_sms(message)
            if not has_sent_sms:
                return False
        return True
    
    def store_refund_customer(self, amount: Decimal, store_id: int):
        PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY

        url = "https://api.paystack.co/refund"

        # convert the overall_price to kobo
        kobo_ammount = amount * Decimal(100)
        data = {
            "transaction": self.order_track_id,
            "amount": float(kobo_ammount),
        }

        print(data)

        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        }

        response = requests.post(url, data=data, headers=headers)
        response = response.json()
        print("refund_user", response)

        if response["status"] == True:
            self.order_payment_status = "pending-refund"
            self.update_store_status(store_id, "pending-refund")
            self.save()

            # notify the user that a refund has been initiated
            self.notify_user(
                message=f"Your refund of {self.order_currency}{amount} has been initiated. The refund will be processed within 24 hours.",
                title="Refund Initiated",
            )

        return response

    # check if a store is linked in any order, if yes, return the orders
    @classmethod
    def get_orders_by_store(cls, store):
        return cls.objects.filter(linked_stores=store, order_payment_status="success")
    # check if a delivery person is linked in any order, if yes, return the orders
    @classmethod
    def get_orders_by_delivery_person(cls, delivery_person):
        return cls.objects.filter(linked_delivery_people=delivery_person)

    # get the number of active orders linked to a delivery person
    @classmethod
    def get_active_orders_count_by_delivery_person(cls, delivery_person):
        return cls.objects.filter(linked_delivery_people=delivery_person).count()

    # re-generate a order_track_id for the order and update the order_track_id of the order
    def regenerate_order_track_id(self):
        self.order_track_id = "order_" + str(uuid.uuid4().hex)[:10]
        self.save()
        return self.order_track_id

    def view_as(self, current_user_profile):
        # check if the current user is among the linked delivery people
        is_delivery_person = self.linked_delivery_people.filter(
            profile=current_user_profile
        ).exists()

        is_vendor = self.linked_stores.filter(vendor=current_user_profile).exists()

        if current_user_profile == self.user and not is_vendor:
            return []

        if current_user_profile == self.user and is_vendor:
            return ["USER", "VENDOR"]

        if is_vendor:
            return ["VENDOR"]
        elif is_delivery_person:
            return ["DELIVERY_PERSON"]
        else:
            return []

    def get_order_status(self, current_user_profile):
        order_status = self.order_status
        view_as = self.view_as(current_user_profile)
        if "DELIVERY_PERSON" in view_as:
            delivery_person = self.get_delivery_person(
                current_user_profile.delivery_person.id
            )
            if delivery_person:
                order_status = delivery_person["status"]
        if "VENDOR" in view_as:
            order_status = self.get_store_status(current_user_profile.store.id)
        return order_status.upper().replace("-", "_") if order_status else "NO_STATUS"

    def update_store_status(self, store_id, status):
        stores_status = self.stores_status
        for store_status in stores_status:
            if str(store_status["storeId"]) == str(store_id):
                store_status["status"] = status
                break
        self.stores_status = stores_status
        self.save()

    # get delivery_person from the delivery_people json
    def get_delivery_person(self, delivery_person_id):
        delivery_people = self.delivery_people
        for delivery_person in delivery_people:
            if delivery_person["id"] == delivery_person_id:
                return delivery_person
        return None

    # get store_status from the stores_status json
    def get_store_status(self, store_id):
        stores_status = self.stores_status
        for store_status in stores_status:
            if str(store_status["storeId"]) == str(store_id):
                return store_status.get("status")
        return None

    # create a payment link for the order
    def create_payment_link(self):
        PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY

        url = "https://api.paystack.co/transaction/initialize"

        # check if order has been initialized before
        if self.order_payment_status == "pending":
            order_track_id = self.regenerate_order_track_id()
        else:
            order_track_id = self.order_track_id
        amount = (
            Decimal(self.overall_price)
            + Decimal(self.delivery_fee)
            + Decimal(self.service_fee)
        )
        amount = amount * 100

        callback_url = f"{FRONTEND_URL}/checkout/{order_track_id}"
        data = {
            "email": self.user.user.email
            if self.user.user.email
            else f"{self.user.user.username}@gmail.com",
            "currency": self.order_currency,
            "amount": Decimal(amount),
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
