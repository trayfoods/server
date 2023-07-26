from django.db import models
from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

# from django.contrib.gis.db import models

from django.db.models.signals import post_save
from trayapp.utils import image_resized

from product.models import Item

from django.conf import settings

User = settings.AUTH_USER_MODEL


class UserAccount(AbstractUser, models.Model):
    password = models.CharField(_("password"), max_length=128, editable=False)
    role = models.CharField(
        max_length=20,
        default="client",
        choices=(
            ("client", "client"),
            ("vendor", "vendor"),
            ("student", "student"),
        ),
    )

class School(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=10, null=True, blank=True)
    slug = models.SlugField(max_length=50, null=True, blank=True)
    location = models.CharField(max_length=50, null=True, blank=True)
    phone_number = models.CharField(max_length=16, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    portal = models.URLField(null=True, blank=True)
    logo = models.ImageField(upload_to="images/school-logo/", null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


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

    @property
    def is_vendor(self):
        return hasattr(self, "vendor")

    def __str__(self) -> str:
        return self.user.username

    def save(self, *args, **kwargs):
        # Resize the image before saving
        if self.image:
            w, h = 300, 300  # Set the desired width and height for the resized image
            img_file, _, _, _ = image_resized(self.image, w, h)
            img_name = self.image.name
            self.image.save(img_name, img_file, save=False)

        super().save(*args, **kwargs)


class Vendor(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=20, null=True, blank=True)
    account_name = models.CharField(max_length=60, null=True, blank=True)
    bank_code = models.CharField(max_length=20, null=True, blank=True)
    country_code = models.CharField(max_length=6, null=True, blank=True)
    balance = models.DecimalField(
        max_digits=100,
        null=True,
        default=00.00,
        decimal_places=2,
        blank=True,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.user.user.username


class Transaction(models.Model):
    TYPE_OF_TRANSACTION = (
        ("reversed", "reversed"),
        ("credit", "credit"),
        ("debit", "debit"),
        ("failed", "failed"),
        ("unknown", "unknown"),
    )
    user = models.OneToOneField(Profile, on_delete=models.CASCADE, editable=False)
    title = models.CharField(max_length=50)
    desc = models.CharField(max_length=200, null=True, blank=True)
    amount = models.DecimalField(
        max_digits=7,
        null=True,
        default=0,
        decimal_places=2,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    _type = models.CharField(max_length=20, choices=TYPE_OF_TRANSACTION)


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
    earnings = models.DecimalField(
        max_digits=7, decimal_places=2, default=0, editable=False
    )
    product_details = models.JSONField(default=dict, editable=False)


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
