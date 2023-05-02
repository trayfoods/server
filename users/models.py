from django.db import models

# from django.contrib.gis.db import models
from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver

from django.db.models.signals import post_save
from trayapp.utils import image_resize

from product.models import Item

from django.conf import settings

User = settings.AUTH_USER_MODEL


class UserAccount(AbstractUser, models.Model):
    role = models.CharField(max_length=20, default="client")


class Gender(models.Model):
    name = models.CharField(max_length=20, help_text="SHOULD BE IN UPPERCASE!")
    rank = models.FloatField(default=0)

    def __str__(self) -> str:
        return self.name


class Store(models.Model):
    store_name = models.CharField(max_length=20)
    store_nickname = models.CharField(max_length=20, null=True, blank=True)
    store_category = models.CharField(max_length=15)
    store_rank = models.FloatField(default=0)
    store_products = models.ManyToManyField(
        "product.Item", related_name="store_items", blank=True
    )
    # store_location = models.PointField(null=True) # Spatial Field Types

    def __str__(self):
        return f"{self.store_nickname}"

    class Meta:
        ordering = ["-store_rank"]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="images/profile-images/", null=True)
    image_hash = models.CharField(
        "Image Hash", editable=False, max_length=32, null=True, blank=True
    )
    phone_number = models.CharField(max_length=16)
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True)
    is_student = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    # location = models.PointField(null=True) # Spatial Field Types

    def __str__(self) -> str:
        return self.user.username

    def save(self, *args, **kwargs):
        if self.image:
            image_resize(self.image, 260, 260)
        super(Profile, self).save(*args, **kwargs)


class Vendor(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=20, null=True, blank=True)
    account_name = models.CharField(max_length=60, null=True, blank=True)
    bank_code = models.CharField(max_length=20, null=True, blank=True)
    country_code = models.CharField(max_length=6, null=True, blank=True)
    balance = models.FloatField(null=True, default=00.00, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.user.user.username


class Transaction(models.Model):
    TYPE_OF_TRANSACTION = (
        ("reversed", "reversed"),
        ("credit", "credit"),
        ("debit", "debit"),
        ("failed", "failed"),
    )
    user = models.OneToOneField(Profile, on_delete=models.CASCADE, editable=False)
    title = models.CharField(max_length=50)
    desc = models.CharField(max_length=200, null=True, blank=True)
    amount = models.FloatField(null=True, default=00.00, blank=True, editable=False)
    _type = models.CharField(max_length=20, choices=TYPE_OF_TRANSACTION)
    created_at = models.DateTimeField(auto_now_add=True)


class Hostel(models.Model):
    name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=10, null=True, blank=True)
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True)
    is_floor = models.BooleanField(default=False)
    floor_count = models.IntegerField(default=0)

    def __str__(self) -> str:
        return self.name


class Client(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    hostel = models.ForeignKey(Hostel, on_delete=models.SET_NULL, null=True)
    room = models.JSONField(default=dict, null=True, blank=True)


class Deliverer(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True)
    extra_details = models.JSONField(default=dict, null=True, blank=True)


ACTIVITY_TYPES = (
    ("view", "view"),
    ("click", "click"),
    ("purchase", "purchase"),
    ("add_to_items", "add_to_items"),
    ("remove_from_order", "remove_from_order"),
    ("add_to_order", "add_to_order"),
    ("remove_from_items", "remove_from_items"),
)


class UserActivity(models.Model):
    user_id = models.PositiveIntegerField()
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    activity_message = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.user_id} - {self.item.product_slug} - {self.timestamp}"

    @property
    def item_idx(self):
        return self.item.id

    @property
    def product_category__name(self):
        return self.item.product_category__name

    @property
    def product_type__name(self):
        return self.item.product_type__name


@receiver(post_save, sender=User)
def update_profile_signal(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()
