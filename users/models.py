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

from trayapp.utils import get_twilio_client

TWILIO_CLIENT = get_twilio_client()

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
    def role(self):
        # check user's role
        profile = Profile.objects.filter(user=self).first()
        is_student = profile.is_student if profile else False
        is_vendor = profile.is_vendor if profile else False
        is_delivery_person = DeliveryPerson.objects.filter(profile=profile).exists() if profile else False

        is_school = School.objects.filter(user=self).exists()

        if is_vendor:
            return "VENDOR"

        if is_delivery_person:
            return "DELIVERY_PERSON"

        if is_student:
            return "STUDENT"

        if is_school:
            return "SCHOOL"

        return "CLIENT"

    def get_delivery_types(self):
        """
        Get the delivery types for the user
        e.g
        ```python
        user = UserAccount.objects.get(username="divine")
        user.get_delivery_types()
        # returns [{'name': 'pickup', 'fee': 0.0}, {'name': 'hostel', 'fee': 100.0}]
        ```
        """
        VALID_DELIVERY_TYPES = settings.VALID_DELIVERY_TYPES
        
        if self.profile.is_student is False:
            # remove hostels from delivery types
            VALID_DELIVERY_TYPES = [
                delivery_type
                for delivery_type in VALID_DELIVERY_TYPES
                if delivery_type.get("name") != "hostel"
            ]
        return VALID_DELIVERY_TYPES

    # get user's orders
    @property
    def orders(self):
        return Order.objects.filter(user=self.profile)

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
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE)
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

    def save(self, *args, **kwargs):
        # make sure the name is in uppercase
        self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(UserAccount, on_delete=models.CASCADE)
    image = models.ImageField(upload_to=profile_image_directory_path, null=True)
    image_hash = models.CharField(
        "Image Hash", editable=False, max_length=32, null=True, blank=True
    )
    country = CountryField(null=True, blank=True, default="NG")
    city = models.CharField(max_length=50, null=True, blank=True)
    state = models.CharField(max_length=10, null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    calling_code = models.CharField(max_length=5, null=True, blank=True)
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True, blank=True)
    phone_number_verified = models.BooleanField(default=False, editable=False)

    
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

        if self.phone_number:
            self.clean_phone_number(self.phone_number)

        super().save(*args, **kwargs)

    @property
    def has_calling_code(self):
        if not self.calling_code and self.country:
            # get the calling code from the country
            from restcountries import RestCountryApiV2 as rapi

            country = rapi.get_country_by_country_code(self.country.code).first()
            calling_code = country.callingCodes[0]
            self.calling_code = calling_code
            self.save()
        return self.calling_code

    @property
    def has_required_fields(self):
        """
        Checking if user has the required fields, which are:
        - School if the user role is equals to 'student'
        - gender
        - country
        - state
        - city
        - phone_number
        """

        if self.is_student:
            student = self.student
            if student.school is None or not student.campus or student.hostel is None or not student.room:
                return False

        if self.gender is None or self.country is None or self.state is None or self.city is None or self.phone_number is None:
            return False

        return True

    @property
    def is_vendor(self):
        return Store.objects.filter(vendor=self).exists()
    
    @property
    def store(self):
        return Store.objects.filter(vendor=self).first()
    
    @property
    def delivery_person(self):
         return DeliveryPerson.objects.filter(profile=self).first()
    
    @property
    def is_student(self):
        return hasattr(self, "student")
    
    def send_phone_number_verification_code(self, new_phone_number, calling_code):
        new_phone_number = new_phone_number.strip()

        # check if the phone number has been used by another user
        self.clean_phone_number(new_phone_number)

        if "+" not in calling_code:
            calling_code = f"+{calling_code}"

        new_phone_number = f"{calling_code}{new_phone_number}"


        verification = TWILIO_CLIENT.verify \
                                .v2 \
                                .services(settings.TWILIO_VERIFY_SERVICE_SID) \
                                .verifications \
                                .create(to=new_phone_number, channel='sms')
        
        success = True if verification.status == "pending" else False

        if success:
            self.phone_number = new_phone_number.replace(calling_code, "")
            self.phone_number_verified = False
            self.save()
        
        return success
    
    def verify_phone_number(self, code, calling_code):
        if "+" not in calling_code:
            calling_code = f"+{calling_code}"

        phone_number = f"{calling_code}{self.phone_number}"

        verification_check = TWILIO_CLIENT.verify \
                                    .v2 \
                                    .services(settings.TWILIO_VERIFY_SERVICE_SID) \
                                    .verification_checks \
                                    .create(to=phone_number, code=code)

        success = True if verification_check.status == "approved" else False

        if success:
            self.phone_number_verified = True
            self.calling_code = calling_code
            self.save()
        
        return success
    
    def send_sms(self, message):
        if self.has_calling_code and self.phone_number_verified:
            phone_number = f"{self.has_calling_code}{self.phone_number}"
            TWILIO_CLIENT.messages.create(
                from_=settings.TWILIO_PHONE_NUMBER,
                body=message,
                to=phone_number
            )
    
    @property
    def is_delivery_person(self):
        return hasattr(self, "delivery_person")
    
    def clean_phone_number(self, phone_number):
        phone_number = phone_number.strip()

        # replace spaces with empty string
        phone_number = phone_number.replace(" ", "")
        
        # check if the phone number has been used by another user
        user_with_phone = Profile.objects.filter(phone_number=phone_number)
        if user_with_phone.exists() and user_with_phone.first().user != self.user:
            raise Exception("Phone number already in use")
        

class Transaction(models.Model):
    TYPE_OF_TRANSACTION = (
        ("credit", "credit"),
        ("debit", "debit"),
    )

    transaction_id = models.UUIDField(
        default=uuid.uuid4, blank=True, editable=False, unique=True
    )
    gateway_transfer_id = models.CharField(
        max_length=50, null=True, blank=True, editable=False, unique=True
    )
    wallet = models.ForeignKey("Wallet", on_delete=models.CASCADE, editable=False)
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True, editable=False
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
        transaction = None
        amount = Decimal(amount)
        transaction_fee = Decimal(transaction_fee)

        if not transaction_id:
            raise Exception("Transaction ID is required")

        transaction_id = uuid.UUID(transaction_id)

        if self.balance < amount:
            raise Exception("Insufficient funds")

        if cleared:
            self.cleared_balance -= amount + transaction_fee
            self.save()
        elif unclear:
            self.uncleared_balance -= amount + transaction_fee
            self.save()
        else:
            # debit the wallet
            self.balance -= amount + transaction_fee
            self.save()

            # check if transaction exists
            transaction = Transaction.objects.filter(
                wallet=self, transaction_id=transaction_id, _type="debit"
            ).first()

            transaction.title = title
            transaction.order = order
            transaction.desc = desc
            transaction.status = status

            transaction.save()
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
    vendor = models.ForeignKey(Profile, on_delete=models.CASCADE)
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

    store_open_hours = models.JSONField(
        default=list, null=True, blank=True, editable=False
    )

    created_at = models.DateTimeField(auto_now_add=True)

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


class Hostel(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, null=True, blank=True, unique=True)
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True)
    campus = models.CharField(max_length=50, null=True, blank=True)
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True)
    is_floor = models.BooleanField(default=False)
    floor_count = models.IntegerField(default=0)

    def __str__(self) -> str:
        return self.name
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.slug:
            self.slug = slugify(self.name)
            self.save()

    @property
    def floors(self):
        # if the hostel is not a floor...we return the floor count in a list
        # else we return the floors in abc order

        if not self.is_floor:
            return [f"flat {i}" for i in range(1, self.floor_count + 1)]
        else:
            # represent the floor_count in alphabets
            floor_count = self.floor_count
            floors = []
            for i in range(1, floor_count + 1):
                floors.append(f"floor {chr(64 + i)}")
            return floors

class Student(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    school = models.ForeignKey(
        School, on_delete=models.SET_NULL, null=True, blank=True
    )
    campus = models.CharField(max_length=50, null=True, blank=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.SET_NULL, null=True, blank=True)
    floor = models.CharField(max_length=50, null=True, blank=True)
    room = models.CharField(max_length=50, null=True, blank=True)


class DeliveryPerson(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, unique=True)
    wallet = models.OneToOneField(
        Wallet, on_delete=models.CASCADE, null=True, blank=True, unique=True
    )
    is_verified = models.BooleanField(default=False)
    is_available = models.BooleanField(default=False)
    is_on_delivery = models.BooleanField(default=False)
    not_allowed_bash = models.JSONField(default=list, null=True, blank=True)
    not_allowed_locations = models.JSONField(default=list, null=True, blank=True)

    def __str__(self) -> str:
        return self.profile.user.username

    class Meta:
        ordering = ["-is_available"]
        verbose_name_plural = "Delivery People"

    # credit delivery person wallet
    def credit_wallet(self, **kwargs):
        self.wallet.add_balance(**kwargs)

    @property
    def orders(self):
        return Order.get_orders_by_delivery_person(delivery_person=self)
    
    # function to check if a order is able ti be delivered by a delivery person
    def can_deliver(self, order):

        order_user = order.user

        # check if the order user is same as the delivery person
        if order_user == self.profile:
            return False
        
        # check if the delivery person is a student and the order user is a student
        if self.profile.is_student and order_user.is_student:
            order_user_gender = order_user.gender.name
            delivery_person_gender = self.profile.gender.name

            if order_user_gender != delivery_person_gender:
                return False


        shipping = order.shipping
        sch = shipping.get("sch")
        address = shipping.get("address")
        bash = shipping.get("bash")

        # check if the delivery person is not allowed to deliver to the order bash
        if bash in self.not_allowed_bash:
            return False
        
        # check if the delivery person is not allowed to deliver to the order location
        if address in self.not_allowed_locations:
            return False
        
        if sch in self.not_allowed_locations:
            return False
        
        return True
    
    # function to get delivery people that can deliver a order
    @staticmethod
    def get_delivery_people_that_can_deliver(order):
        delivery_people = DeliveryPerson.objects.filter(is_available=True, is_on_delivery=False)
        delivery_people_that_can_deliver = []
        for delivery_person in delivery_people:
            if delivery_person.can_deliver(order):
                delivery_people_that_can_deliver.append(delivery_person)
        return delivery_people_that_can_deliver




class UserActivity(models.Model):
    ACTIVITY_TYPES = (
        ("view", "view"),
        ("click", "click"),
        ("purchase", "purchase"),
        ("add_to_items", "add_to_items"),
        ("remove_from_order", "remove_from_order"),
        ("add_to_order", "add_to_order"),
        ("remove_from_items", "remove_from_items"),
    )
    user_id = models.PositiveIntegerField()
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    activity_message = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

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
@receiver(post_save, sender=UserAccount)
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
            wallet = Wallet.objects.filter(user=instance.profile).first()
            if not wallet:
                wallet = Wallet.objects.create(user=instance.profile)
                wallet.save()
            instance.wallet = wallet
            instance.wallet.save()


@receiver(post_save, sender=Store)
def update_store_wallet_signal(sender, instance, created, **kwargs):
    if created:
        # check if wallet exists
        if not instance.wallet:
            # check if user has a wallet
            wallet = Wallet.objects.filter(user=instance.vendor).first()
            if not wallet:
                wallet = Wallet.objects.create(user=instance.vendor)
                wallet.save()
            instance.wallet = wallet
            instance.wallet.save()


@receiver(models.signals.post_delete, sender=Profile)
def remove_file_from_s3(sender, instance, using, **kwargs):
    try:
        instance.image.delete(save=False)
    except:
        pass
