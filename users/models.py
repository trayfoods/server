import os

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

# from django.contrib.gis.db import models
from django.template.defaultfilters import slugify
from django.db.models.signals import post_save
from trayapp.utils import image_resized

from product.models import Item, Order

from django.conf import settings

User = settings.AUTH_USER_MODEL


def profile_image_directory_path(instance, filename):
    """
    Create a directory path to upload the Profile Image.
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


class UserAccount(AbstractUser, models.Model):
    password = models.CharField(_("password"), max_length=128, editable=False)
    role = models.CharField(
        _("role"),
        max_length=20,
        default="client",
        choices=(
            ("client", "client"),
            ("vendor", "vendor"),
            ("student", "student"),
        ),
    )

    # get user's orders
    @property
    def orders(self):
        return Order.objects.filter(user=self)


class School(models.Model):
    user = models.OneToOneField("Profile", on_delete=models.CASCADE)
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


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to=profile_image_directory_path, null=True)
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


class Wallet(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    currency = models.CharField(max_length=4, default="NGN")
    balance = models.DecimalField(
        max_digits=100,
        null=True,
        default=00.00,
        decimal_places=2,
        blank=True,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.user.user.username

    # get user's transactions
    @property
    def transactions(self):
        return Transaction.objects.filter(user=self)

    @property
    def add_balance(self, amount, desc=None):
        self.balance += amount
        self.save()
        desc = desc if desc else f"Added {self.currency} {amount} to wallet"
        # create a transaction
        transaction = Transaction.objects.create(
            user=self.user,
            title="Wallet Funding",
            desc=desc,
            amount=amount,
            _type="credit",
        )
        transaction.save()
        return transaction

    @property
    def deduct_balance(self, amount, desc=None):
        self.balance -= amount
        self.save()
        desc = desc if desc else f"Deducted {self.currency} {amount} from wallet"
        # create a transaction
        transaction = Transaction.objects.create(
            user=self.user,
            title="Wallet Debit",
            desc=desc,
            amount=amount,
            _type="debit",
        )
        transaction.save()
        return transaction

    @property
    def reverse_transaction(self, amount, desc=None):
        self.balance += amount
        self.save()
        desc = desc if desc else f"Reversed {self.currency} {amount} to wallet"
        # create a transaction
        transaction = Transaction.objects.create(
            user=self.user,
            title="Wallet Reversal",
            desc=desc,
            amount=amount,
            _type="reversed",
        )
        transaction.save()
        return transaction


class Store(models.Model):
    wallet = models.OneToOneField(
        Wallet, on_delete=models.CASCADE, null=True, blank=True
    )
    vendor = models.OneToOneField("Vendor", on_delete=models.CASCADE)
    store_name = models.CharField(max_length=20)
    store_nickname = models.CharField(max_length=20, null=True, blank=True)
    store_category = models.CharField(max_length=15)
    store_rank = models.FloatField(default=0)
    store_products = models.ManyToManyField(
        "product.Item", related_name="store_items", blank=True
    )
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    # store_location = models.PointField(null=True) # Spatial Field Types

    def __str__(self):
        return f"{self.store_nickname}"

    class Meta:
        ordering = ["-store_rank"]


class Vendor(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=20, null=True, blank=True)
    account_name = models.CharField(max_length=60, null=True, blank=True)
    bank_code = models.CharField(max_length=20, null=True, blank=True)
    country_code = models.CharField(max_length=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.user.user.username

    # get vendor's store
    @property
    def store(self):
        return Store.objects.get(vendor=self)


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


class DeliveryPerson(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE, unique=True)
    wallet = models.OneToOneField(
        Wallet, on_delete=models.CASCADE, null=True, blank=True, unique=True
    )
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True)
    is_verified = models.BooleanField(default=False)
    is_available = models.BooleanField(default=False)
    is_on_delivery = models.BooleanField(default=False)
    orders = models.ManyToManyField("product.Order", blank=True)

    def __str__(self) -> str:
        return self.user.user.username

    class Meta:
        ordering = ["-is_available"]
        verbose_name_plural = "Delivery People"


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

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "User Activities"

    @property
    def item_idx(self):
        return self.item.id

    @property
    def product_category__name(self):
        return self.item.product_category__name

    @property
    def product_type__name(self):
        return self.item.product_type__name


# Signals
@receiver(post_save, sender=User)
def update_profile_signal(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()


# create a wallet for delivery person and store
@receiver(post_save, sender=DeliveryPerson)
def update_delivery_person_wallet_signal(sender, instance, created, **kwargs):
    if created:
        # check if wallet exists
        if not instance.wallet:
            # check if user has a wallet
            wallet = Wallet.objects.filter(user=instance.user).first()
            if not wallet:
                wallet = Wallet.objects.create(user=instance.user)
                wallet.save()
            instance.wallet = wallet
            instance.wallet.save()


@receiver(post_save, sender=Store)
def update_store_wallet_signal(sender, instance, created, **kwargs):
    if created:
        # check if wallet exists
        if not instance.wallet:
            # check if user has a wallet
            wallet = Wallet.objects.filter(user=instance.vendor.user).first()
            if not wallet:
                wallet = Wallet.objects.create(user=instance.vendor.user)
                wallet.save()
            instance.wallet = wallet
            instance.wallet.save()


@receiver(models.signals.post_delete, sender=Profile)
def remove_file_from_s3(sender, instance, using, **kwargs):
    try:
        instance.image.delete(save=False)
    except:
        pass
