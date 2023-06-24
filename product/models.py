import os
import uuid
from django.db import models
from django.dispatch import receiver
from django.template.defaultfilters import slugify
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import datetime

User = settings.AUTH_USER_MODEL

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
        ordering = ["-id"]

    def __str__(self) -> str:
        return self.product.product_slug

    # def save(self, *args, **kwargs):
    #     super(ItemImage, self).save(*args, **kwargs)


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
    #     food_categories = [
    #     "Fast Food",
    #     "Asian Cuisine",
    #     "Italian Cuisine",
    #     "American Cuisine",
    #     "Mexican Cuisine",
    #     "Healthy and Salad Options",
    #     "Desserts and Sweets",
    #     "Breakfast and Brunch",
    #     "Middle Eastern Cuisine",
    #     "Beverages"
    # ]

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
    name = models.CharField(max_length=20)
    urlParamName = models.SlugField(null=False, unique=True)
    _type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):  # auto create urlParamName
        if not self.urlParamName:
            self.urlParamName = slugify(self.urlParamName)
        return super().save(*args, **kwargs)


class Order(models.Model):
    order_id = models.CharField(
        max_length=17,
        unique=True,
        primary_key=True,
        editable=False,
    )
    order_user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_details = models.JSONField(default=dict, null=True, blank=True)
    order_payment_id = models.CharField(max_length=20, null=True, blank=True)
    order_payment_currency = models.CharField(max_length=20, null=True, blank=True)
    order_payment_method = models.CharField(max_length=20, null=True, blank=True)
    order_payment_status = models.CharField(
        max_length=20,
        default="pending",
        choices=(("failed", "failed"), ("success", "success"), ("pending", "pending")),
    )
    order_created_on = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.order_id:
            # Generate a custom ID if it doesn't exist
            self.order_id = self.generate_order_id()
        super().save(*args, **kwargs)

    def generate_order_id(self):
        # Get the current date
        current_date = datetime.date.today()
        year = current_date.year
        # Implement order ID generation logic here
        # For example, you can use a combination of static value and random number
        return f"{str(year)}-" + str(uuid.uuid4().hex)[:10]

    def __str__(self):
        return "Order #" + str(self.order_id)


# Signals
@receiver(models.signals.post_delete, sender=ItemImage)
def remove_file_from_s3(sender, instance, using, **kwargs):
    instance.item_image.delete(save=False)
