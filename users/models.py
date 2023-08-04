from decimal import Decimal
import os

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

# from django.contrib.gis.db import models
from django.template.defaultfilters import slugify
from django.db.models.signals import post_save
from trayapp.utils import image_resized, image_exists

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
    username = slugify(instance.user.username)
    _, extension = os.path.splitext(filename)
    return f"images/users/{username}/{username}{extension}"


def school_logo_directory_path(instance, filename):
    """
    Create a directory path to upload the School Logo.
    :param object instance:
        The instance where the current file is being attached.
    :param str filename:
        The filename that was originally given to the file.
        This may not be taken into account when determining
        the final destination path.
    :result str: Directory path.file_extension.
    """
    school_name = slugify(instance.name)
    _, extension = os.path.splitext(filename)
    return f"images/school-logo/{school_name}/{school_name}{extension}"


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
            ("school", "school"),
            ("delivery", "delivery"),
        ),
    )

    # get user's orders
    @property
    def orders(self):
        return Order.objects.filter(user=self)


class Country(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=5, null=True, blank=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name_plural = "Countries"


class School(models.Model):
    user = models.OneToOneField(UserAccount, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=10, null=True, blank=True)
    slug = models.SlugField(max_length=50, null=True, blank=True)
    address = models.CharField(max_length=50, null=True, blank=True)
    country = models.ForeignKey(
        Country, on_delete=models.SET_NULL, null=True, blank=True
    )
    phone_number = models.CharField(max_length=16, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    portal = models.URLField(null=True, blank=True)
    logo = models.ImageField(
        upload_to=school_logo_directory_path, null=True, blank=True
    )
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
    school = models.ForeignKey(
        School, on_delete=models.SET_NULL, null=True, blank=True, editable=False
    )
    country = models.ForeignKey(
        Country, on_delete=models.SET_NULL, null=True, blank=True
    )
    phone_number = models.CharField(max_length=16)
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True)
    is_student = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    @property
    def is_vendor(self):
        return hasattr(self, "vendor")

    def __str__(self) -> str:
        return self.user.username

    def save(self, *args, **kwargs):
        # Resize the image before saving
        if self.image:
            w, h = 300, 300  # Set the desired width and height for the resized image
            if image_exists(self.image.name):
                img_file, _, _, _ = image_resized(self.image, w, h)
                if img_file:
                    img_name = self.image.name
                    self.image.save(img_name, img_file, save=False)

        super().save(*args, **kwargs)


class Transaction(models.Model):
    TYPE_OF_TRANSACTION = (
        ("refund", "refund"),
        ("credit", "credit"),
        ("debit", "debit"),
        ("failed", "failed"),
        ("unknown", "unknown"),
    )
    wallet = models.ForeignKey("Wallet", on_delete=models.CASCADE, editable=False)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, null=True, blank=True, editable=False
    )
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

    # check if the transaction is for a order
    @property
    def is_order(self):
        return hasattr(self, "order")


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
    uncleared_balance = models.DecimalField(
        max_digits=100,
        null=True,
        default=00.00,
        decimal_places=2,
        blank=True,
        editable=False,
    )
    cleared_balance = models.DecimalField(
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

    # add balance to user's wallet
    def add_balance(self, **kwargs):
        amount = kwargs.get("amount")
        title = kwargs.get("title", None)
        desc = kwargs.get("desc", None)
        order = kwargs.get("order", None)
        unclear = kwargs.get("unclear", False)
        cleared = kwargs.get("cleared", False)
        transaction = None
        amount = Decimal(amount)
        if cleared:
            self.cleared_balance += amount
            self.save()
        elif unclear:
            self.uncleared_balance += amount
            self.save()
        else:
            # convert the amount to decimal
            self.balance += amount
            self.save()
            # create a transaction
            transaction = Transaction.objects.create(
                wallet=self,
                title="Wallet Credited" if not title else title,
                desc=f"{amount} {self.currency} was added to wallet"
                if not desc
                else desc,
                amount=amount,
                order=order,
                _type="credit",
            )
            transaction.save()
        return transaction

    def clear_balance(self, type):
        list_of_actions = ["cleared", "uncleared"]
        if type in list_of_actions:
            if type == "cleared":
                self.cleared_balance = Decimal(0.00)
            else:
                self.uncleared_balance = Decimal(0.00)
            self.save()

    def deduct_balance(self, **kwargs):
        amount = kwargs.get("amount")
        title = kwargs.get("title", None)
        desc = kwargs.get("desc", None)
        order = kwargs.get("order", None)
        unclear = kwargs.get("unclear", False)
        cleared = kwargs.get("cleared", False)
        transaction = None
        amount = Decimal(amount)
        if cleared:
            self.cleared_balance -= amount
            self.save()
        elif unclear:
            self.uncleared_balance -= amount
            self.save()
        else:
            self.balance -= amount
            self.save()
            # create a transaction
            transaction = Transaction.objects.create(
                wallet=self,
                title="Wallet Debited" if not title else title,
                desc=f"Deducted {self.currency} {amount} from wallet" if not desc else desc,
                order=order,
                amount=amount,
                _type="debit",
            )
            transaction.save()
        return transaction

    def refund_transaction(self, **kwargs):
        amount = kwargs.get("amount")
        title = kwargs.get("title", None)
        desc = kwargs.get("desc", None)
        order = kwargs.get("order", None)
        unclear = kwargs.get("unclear", False)
        cleared = kwargs.get("cleared", False)
        transaction = None
        amount = Decimal(amount)
        if cleared:
            self.cleared_balance += amount
            self.save()
        elif unclear:
            self.uncleared_balance += amount
            self.save()
        else:
            self.balance += amount
            self.save()
            # create a transaction
            transaction = Transaction.objects.create(
                wallet=self,
                title="Wallet Credited" if not title else title,
                desc=f"{amount} {self.currency} was refunded to your wallet"
                if not desc
                else desc,
                amount=amount,
                order=order,
                _type="refund",
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

    # credit store wallet
    def credit_wallet(self, **kwargs):
        print(kwargs)
        return self.wallet.add_balance(**kwargs)

    @property
    def orders(self):
        return Order.get_orders_by_store(store=self)


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
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True)
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

    # credit delivery person wallet
    def credit_wallet(self, **kwargs):
        self.wallet.add_balance(**kwargs)


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
