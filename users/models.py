from decimal import Decimal
import os
import uuid

from django.db import models
from django_countries.fields import CountryField
from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

# from django.contrib.gis.db import models
from django.template.defaultfilters import slugify
from django.db.models.signals import post_save
from users.signals import balance_updated
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


def store_cover_image_directory_path(instance, filename):
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
    username = slugify(instance.vendor.user.user.username)
    _, extension = os.path.splitext(filename)
    return f"images/vendors/{username}/{instance.store_nickname}-store-cover{extension}"


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
    email = models.EmailField(_("email address"), blank=True, unique=True)
    password = models.CharField(_("password"), max_length=128, editable=False)

    REQUIRED_FIELDS = ["email", "first_name", "last_name"]

    @property
    def role(self):  # set user role
        role = "client"
        user = UserAccount.objects.filter(id=self.id).first()
        profile = Profile.objects.filter(user=user).first()
        vendor = Vendor.objects.filter(user=profile).first()
        student = Student.objects.filter(user=profile).first()
        school = School.objects.filter(user=user).first()
        delivery_person = DeliveryPerson.objects.filter(user=profile).first()

        if (
            student is None
            and vendor is None
            and school is None
            and delivery_person is None
        ):
            role = "client"

        if not vendor is None:
            role = "vendor"

        if not student is None and vendor is None:
            role = "student"

        if not school is None and vendor is None:
            role = "school"

        if not delivery_person is None and vendor is None and school is None:
            role = "delivery_person"

        return role.upper()  # DO NOT TOUCH THIS

    # get user's orders
    @property
    def orders(self):
        return Order.objects.filter(user=self)

    # get user's devices
    @property
    def devices(self):
        return UserDevice.objects.filter(user=self)

    def add_device(self, **kwargs):
        # check if user is in kwargs
        if "user" in kwargs:
            raise Exception("User is not required in kwargs")
        # check if device already exists
        if UserDevice.objects.filter(user=self, **kwargs).exists():
            raise UserDevice.objects.filter(user=self, **kwargs).first()
        return UserDevice.objects.create(user=self, **kwargs)


class UserDevice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    device_token = models.TextField()
    device_type = models.CharField(max_length=100, null=True, blank=True)
    device_name = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user.username}'s {self.device_type}"


class School(models.Model):
    user = models.OneToOneField(UserAccount, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    email = models.EmailField(null=True, blank=True)
    country = CountryField(default="NG")
    campuses = models.JSONField(default=list, null=True, blank=True, editable=True)
    slug = models.SlugField(max_length=50, null=True, blank=True, unique=True)
    phone_numbers = models.JSONField(
        default=list, null=True, blank=True, editable=False
    )
    domains = models.JSONField(default=list, null=True, blank=True, editable=False)
    logo = models.ImageField(
        upload_to=school_logo_directory_path, null=True, blank=True
    )
    is_verified = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.slug:
            self.slug = slugify(self.name)
            self.save()


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
    country = CountryField(null=True, blank=True, default="NG")
    city = models.CharField(max_length=50, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    phone_number = models.CharField(max_length=16)
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True)
    is_verified = models.BooleanField(default=False)

    def has_required_fields(self):
        """
        Check if user has the required fields, which are:
        - School if the user role is equals to 'student'
        - gender
        - country
        - phone_number
        """

        if self.user.role == "student":
            if self.school is None:
                return False

        if self.gender is None:
            return False

        if self.country is None:
            return False

        if self.phone_number is None:
            return False

        return True

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
        ("credit", "credit"),
        ("debit", "debit"),
    )

    transaction_id = models.UUIDField(
        default=uuid.uuid4, blank=True, editable=False, null=True
    )
    gateway_transfer_id = models.CharField(
        max_length=50, null=True, blank=True, editable=False
    )
    wallet = models.ForeignKey("Wallet", on_delete=models.CASCADE, editable=False)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, null=True, blank=True, editable=False
    )
    currency = models.CharField(max_length=4, default="NGN", editable=False)
    title = models.CharField(max_length=50)
    desc = models.CharField(max_length=200, null=True, blank=True)
    amount = models.DecimalField(
        max_digits=7,
        default=0,
        decimal_places=2,
        editable=False,
    )
    transaction_fee = models.DecimalField(
        max_digits=7,
        default=0,
        decimal_places=2,
        editable=False,
    )
    status = models.CharField(
        max_length=20,
        choices=(
            ("success", "success"),
            ("failed", "failed"),
            ("pending", "pending"),
            ("reversed", "reversed"),
        ),
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_on = models.DateTimeField(auto_now=True, editable=False)
    _type = models.CharField(max_length=20, choices=TYPE_OF_TRANSACTION)

    class Meta:
        ordering = ["-created_at", "-updated_on"]

    # check if the transaction is for a order
    @property
    def is_order(self):
        return hasattr(self, "order")

    def get_by_order(self, order):
        return Transaction.objects.filter(order=order).first()

    def get_by_wallet(self, wallet):
        return Transaction.objects.filter(wallet=wallet).first()


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
    passcode = models.CharField(
        _("passcode"), max_length=128, editable=False, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.user.user.username

    def save(self, *args, **kwargs):
        # Emit the balance_updated signal
        if (
            "balance" in self.get_dirty_fields()
        ):  # You might need to implement get_dirty_fields() method
            balance_updated.send(sender=self.__class__, balance=self.balance)

        super().save(*args, **kwargs)

    # set passcode for wallet
    def set_passcode(self, passcode):
        """
        Set the passcode for the wallet
        e.g
        ```
        wallet = Wallet.objects.get(user__username="divine")
        wallet.set_passcode("1234")
        ```
        """
        from django.contrib.auth.hashers import make_password

        self.passcode = make_password(passcode)
        self.save()

    def check_passcode(self, passcode):
        """
        Check if the passcode is correct
        e.g
        ```
        wallet = Wallet.objects.get(user__username="divine")
        wallet.check_passcode("0000")
        # returns True if the passcode is correct
        ```
        """
        from django.contrib.auth.hashers import check_password

        # check if passcode is set
        if self.passcode is None:
            # set passcode to 0000
            self.set_passcode("0000")

        return check_password(passcode, self.passcode)

    def get_dirty_fields(self):
        """
        Returns a dictionary of field_name->(old_value, new_value) for each
        field that has changed.
        """
        dirty_fields = {}
        for field in self._meta.fields:
            field_name = field.attname
            if field_name == "id":
                continue
            old_value = getattr(self, field_name)
            new_value = getattr(self, field_name)
            if old_value != new_value:
                dirty_fields[field_name] = (old_value, new_value)

        return dirty_fields

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
                status="success",
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
        transaction_fee = kwargs.get("transaction_fee", 0.00)
        title = kwargs.get("title", "Wallet Debited")
        desc = kwargs.get(
            "desc", f"{self.currency} {amount} was deducted from your wallet"
        )
        transaction_id = kwargs.get("transaction_id", None)
        order = kwargs.get("order", None)
        status = kwargs.get("status", "pending")
        unclear = kwargs.get("unclear", False)
        cleared = kwargs.get("cleared", False)
        nor_debit_wallet = kwargs.get("nor_debit_wallet", False)  # do not debit wallet
        transaction = None
        amount = Decimal(amount)
        transaction_fee = Decimal(transaction_fee)

        if not transaction_id:
            raise Exception("Transaction ID is required")

        if self.balance < amount:
            raise Exception("Insufficient funds")

        if cleared:
            self.cleared_balance -= amount + transaction_fee
            self.save()
        elif unclear:
            self.uncleared_balance -= amount + transaction_fee
            self.save()
        else:
            if nor_debit_wallet != True:  # check if the wallet should be debited
                # debit the wallet
                self.balance -= amount + transaction_fee
                self.save()
            # check if transaction exists
            transaction = Transaction.objects.filter(
                wallet=self, transaction_id=transaction_id, _type="debit"
            ).first()

            transaction.title = title
            transaction.desc = desc
            transaction.status = status

            transaction.save()
            if transaction_id and transaction_id != transaction.transaction_id:
                # delete the transaction
                transaction.delete()
                raise Exception("Something went wrong, please try again later")
        return transaction

    def reverse_transaction(self, **kwargs):
        amount = kwargs.get("amount")
        title = kwargs.get("title", "Transfer Reversed")

        currency_symbol = "₦" if self.currency == "NGN" else None
        currency = self.currency if currency_symbol is None else ""
        desc = kwargs.get(
            "desc", f"{currency_symbol}{amount} {currency} was reversed to your wallet"
        )

        order = kwargs.get("order", None)
        transaction_id = kwargs.get("transaction_id", None)
        unclear = kwargs.get("unclear", False)
        cleared = kwargs.get("cleared", False)

        transaction = Transaction.objects.filter(transaction_id=transaction_id).first()

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

            if transaction is None:
                # create a transaction
                transaction = Transaction.objects.create(
                    wallet=self,
                    title=title,
                    status="reversed",
                    amount=amount,
                    order=order,
                    _type="debit",
                )
            transaction.title = title
            transaction.desc = desc
            transaction.save()
        return transaction


class Store(models.Model):
    wallet = models.OneToOneField(
        Wallet, on_delete=models.CASCADE, null=True, blank=True
    )
    vendor = models.ForeignKey("Vendor", on_delete=models.CASCADE)
    store_name = models.CharField(max_length=100)
    store_country = CountryField(default="NG")
    store_type = models.CharField(max_length=20, null=True, blank=True)
    store_categories = models.JSONField(
        default=list, null=True, blank=True, editable=False
    )
    store_phone_numbers = models.JSONField(
        default=list, null=True, blank=True, editable=False
    )
    store_bio = models.CharField(null=True, blank=True, max_length=150)
    store_address = models.CharField(max_length=60, null=True, blank=True)
    store_nickname = models.CharField(max_length=50, null=True, blank=True)
    store_school = models.ForeignKey(
        School, on_delete=models.SET_NULL, null=True, blank=True
    )
    store_cover_image = models.ImageField(
        upload_to=store_cover_image_directory_path, null=True, blank=True
    )
    store_rank = models.FloatField(default=0)

    def __str__(self):
        return f"{self.store_nickname}"

    class Meta:
        ordering = ["-store_rank"]

    def save(self, *args, **kwargs):
        # Resize the image before saving
        if self.store_cover_image:
            w, h = 1024, 300  # Set the desired width and height for the resized image
            if image_exists(self.store_cover_image.name):
                img_file, _, _, _ = image_resized(self.store_cover_image, w, h)
                if img_file:
                    img_name = self.store_cover_image.name
                    self.store_cover_image.save(img_name, img_file, save=False)

        super().save(*args, **kwargs)

    # is store a school store
    @property
    def is_school_store(self):
        return True if self.store_school else False

    # get store's products
    @property
    def store_products(self):
        return Item.get_items_by_store(store=self)

    # credit store wallet
    def credit_wallet(self, **kwargs):
        return self.wallet.add_balance(**kwargs)

    @property
    def orders(self):
        return Order.get_orders_by_store(store=self)


class Vendor(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=20, null=True, blank=True)
    account_name = models.CharField(max_length=60, null=True, blank=True)
    bank_code = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.user.user.username

    # get vendor's store
    @property
    def store(self):
        return Store.objects.get(vendor=self)

    def is_store_owner(self, store):
        return True if store.vendor == self else False


class Hostel(models.Model):
    name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=10, null=True, blank=True)
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True)
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True)
    is_floor = models.BooleanField(default=False)
    floor_count = models.IntegerField(default=0)

    def __str__(self) -> str:
        return self.name


class Student(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    school = models.ForeignKey(
        School, on_delete=models.SET_NULL, null=True, blank=True, editable=False
    )
    campus = models.CharField(max_length=50, null=True, blank=True)
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
    # orders = models.ManyToManyField("product.Order", blank=True)

    def __str__(self) -> str:
        return self.user.user.username

    class Meta:
        ordering = ["-is_available"]
        verbose_name_plural = "Delivery People"

    # credit delivery person wallet
    def credit_wallet(self, **kwargs):
        self.wallet.add_balance(**kwargs)

    @property
    def orders(self):
        return Order.get_orders_by_delivery_person(delivery_person=self)


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
