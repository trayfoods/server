from decimal import Decimal
import os
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template

import uuid
import pytz
import logging

from django.utils import timezone

from django.db import models
from django_countries.fields import CountryField
from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from django.template.defaultfilters import slugify
from django.db.models.signals import post_save
from users.signals import balance_updated
from trayapp.utils import image_resized, image_exists, termii_send_sms

from product.models import Item, Order

from datetime import datetime
from django.conf import settings

from trayapp.utils import get_twilio_client, send_notification_to_queue
from django.contrib.auth.hashers import check_password, make_password

TWILIO_CLIENT = get_twilio_client()
SMS_ENABLED = settings.SMS_ENABLED


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
    _, extension = os.path.splitext(filename)
    return f"images/users/{instance.id}/profile/{instance.id}-profile-image{extension}"


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
    _, extension = os.path.splitext(filename)
    return f"images/users/{instance.vendor.user.id}/store/{instance.store_nickname}-store-cover{extension}"


class UserAccount(AbstractUser, models.Model):
    email = models.EmailField(_("email address"), blank=True, unique=True)
    password = models.CharField(_("password"), max_length=128, editable=False)

    REQUIRED_FIELDS = ["email", "first_name", "last_name"]

    @property
    def roles(self):
        # check user's roles
        profile = Profile.objects.filter(user=self).first()
        is_student = profile.is_student if profile else False
        is_vendor = profile.is_vendor if profile else False
        is_delivery_person = (
            DeliveryPerson.objects.filter(profile=profile).exists()
            if profile
            else False
        )

        roles = []

        if is_vendor:
            roles.append("VENDOR")

        if is_delivery_person:
            roles.append("DELIVERY_PERSON")

        if is_student:
            roles.append("STUDENT")

        if not roles:
            roles.append("CLIENT")

        return roles

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

        # check if user is not a student
        if not "STUDENT" in self.roles:
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

    @property
    def has_token_device(self):
        return UserDevice.objects.filter(user=self).exists()

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
    is_active = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user.username}'s {self.device_type}"


class School(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, null=True, blank=True, unique=True)
    country = CountryField(default="NG")
    campuses = models.JSONField(default=list, null=True, blank=True, editable=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.slug:
            self.slug = slugify(self.name)
            self.save()

    @property
    def hostels(self):
        return Hostel.objects.filter(school=self)

    @property
    def hostel_fields(self):
        return HostelField.objects.filter(school=self)


class HostelField(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=10)
    placeholder = models.CharField(max_length=100, blank=True)
    options = models.JSONField(default=list, null=True, blank=True)
    loop_prefix = models.CharField(max_length=10, blank=True, help_text="e.g Room")
    value_prefix = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Not required if loop_prefix is set",
    )
    is_loop = models.BooleanField(default=False)
    loop_range = models.IntegerField(blank=True, null=True)
    loop_suffix = models.CharField(
        max_length=10,
        choices=(("number", "number"), ("alphabet", "alphabet")),
        blank=True,
    )

    def __str__(self) -> str:
        return f"{self.name}".upper()

    # value_prefix and loop_prefix cannot be set at the same time
    def save(self, *args, **kwargs):
        if self.value_prefix and self.loop_prefix:
            raise Exception(
                "Value Prefix and Loop Prefix cannot be set at the same time"
            )
        super().save(*args, **kwargs)

    class Meta:
        # set singular and plural names
        verbose_name = "Hostel Arrangement Field"
        verbose_name_plural = "Hostel Arrangement Fields"

    def get_options(self):
        # check if the field is not a loop
        if not self.is_loop:
            return self.options

        if self.loop_suffix == "number":
            return [f"{self.loop_prefix} {i}" for i in range(1, self.loop_range + 1)]

        elif self.loop_suffix == "alphabet":
            # represent the self.loop_range in alphabets
            return [
                f"{self.loop_prefix} {chr(64 + i)}"
                for i in range(1, self.loop_range + 1)
            ]


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
    image = models.ImageField(
        upload_to=profile_image_directory_path, null=True, blank=True
    )
    country = CountryField(null=True, blank=True, default="NG")
    city = models.CharField(max_length=50, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    primary_address = models.CharField(max_length=255, null=True, blank=True)
    street_name = models.CharField(max_length=50, null=True, blank=True)
    primary_address_lat = models.FloatField(null=True, blank=True)
    primary_address_lng = models.FloatField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    calling_code = models.CharField(max_length=5, null=True, blank=True)
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True, blank=True)
    phone_number_verified = models.BooleanField(default=False, editable=False)
    has_required_fields = models.BooleanField(default=False, editable=False)

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

    def has_calling_code(self):
        calling_code = self.calling_code

        if not calling_code and self.country:
            # get the calling code from the country
            from restcountries import RestCountryApiV2 as rapi

            country = rapi.get_country_by_country_code(self.country.code)
            calling_code: str = country.calling_codes[0]

            self.calling_code = calling_code
            self.save()

        if "+" in calling_code:
            calling_code = calling_code.replace("+", "")
            self.calling_code = calling_code
            self.save()

        return True if calling_code else False

    def get_full_phone_number(self):
        return f"{self.calling_code}{self.phone_number}"

    def get_required_fields(self):
        """
        Checking if user has the required fields, which are:
        - if the user roles is equals to 'student' check if the user has:
            - school
            - campus
            - hostel
            - hostel fields
        - Phone Number
        - Country
        - State
        - City
        - Gender
        - Primary Address
        - Street Name
        - Primary Address Lat
        - Primary Address Lng

        Returns a list of the required fields that are not filled
        """
        required_fields = []

        # if self.has_required_fields:
        #     return required_fields

        if self.is_student:
            if not self.student.school:
                required_fields.append("school")
            if not self.student.campus:
                required_fields.append("campus")
            if not self.student.hostel:
                required_fields.append("hostel")
            if not self.student.hostel_fields or len(self.student.hostel_fields) == 0:
                required_fields.append("hostelFields")
        else:  # check if the user is not a student
            if not self.state:
                required_fields.append("state")
            if not self.city:
                required_fields.append("city")

            if not self.primary_address:
                required_fields.append("primaryAddress")
            if not self.primary_address_lat:
                required_fields.append("primaryAddressLat")
            if not self.primary_address_lng:
                required_fields.append("primaryAddressLng")

        if not self.country:
            required_fields.append("country")

        if not self.phone_number:
            required_fields.append("phoneNumber")

        # set has_required_fields to True if required_fields is empty
        if not required_fields:
            self.has_required_fields = True
            self.save()

        return required_fields

    @property
    def is_vendor(self):
        return self.store is not None

    @property
    def store(self):
        return Store.objects.filter(vendor=self).first()

    def get_wallet(self):
        return Wallet.objects.filter(user=self).first()

    def get_delivery_person(self):
        return DeliveryPerson.objects.filter(profile=self).first()

    @property
    def is_student(self):
        return hasattr(self, "student")

    def send_phone_number_verification_code(self, new_phone_number, calling_code):
        new_phone_number = new_phone_number.strip()

        # check if the phone number has been used by another user
        self.clean_phone_number(new_phone_number)

        new_phone_number = f"{calling_code}{new_phone_number}"

        verification = TWILIO_CLIENT.verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verifications.create(to=new_phone_number, channel="sms")

        success = True if verification.status == "pending" else False

        if success:
            self.phone_number = new_phone_number.replace(calling_code, "")
            self.phone_number_verified = False
            self.save()

        return success

    def verify_phone_number(self, code, calling_code):

        phone_number = f"{calling_code}{self.phone_number}"

        verification_check = TWILIO_CLIENT.verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verification_checks.create(to=phone_number, code=code)

        success = True if verification_check.status == "approved" else False

        if success:
            self.phone_number_verified = True
            self.calling_code = calling_code
            self.save()

        return success

    def send_sms(self, message):
        try:
            if SMS_ENABLED and (self.has_calling_code() and self.phone_number_verified):
                phone_number = f"{self.calling_code}{self.phone_number}"
                termii_send_sms(to=phone_number, msg=message, channel="dnd")

                # TWILIO_CLIENT.messages.create(
                #     body=message, from_=settings.TWILIO_PHONE_NUMBER, to=phone_number
                # )
                return True

            if not SMS_ENABLED:
                logging.error("SMS is disabled")
                print(message)
                logging.info("End of SMS is disabled")
                return False if not settings.DEBUG else True
        except Exception as e:
            print(e)
            return False

    def send_push_notification(self, title, msg, data=None):
        user = self.user
        if not user.has_token_device:
            return False

        user_devices = UserDevice.objects.filter(user=user, is_active=True).values_list(
            "device_token", flat=True
        )
        device_tokens = list(user_devices)
        try:
            from .threads import FCMThread

            FCMThread(
                title=title,
                msg=msg,
                tokens=device_tokens,
                data=(
                    data
                    if data
                    else {
                        "priority": "high",
                        "sound": "default",
                    }
                ),
            ).start()
            return True
        except:
            return False

    def notify_me(self, title, msg, data=None, skip_email=False):
        if not self.send_push_notification(title, msg, data):
            from_email = settings.DEFAULT_FROM_EMAIL
            template = None
            if data:
                from_email = data.get("from_email", None) or from_email
                template = data.get("template", None)
            did_send_sms = self.send_sms(message=msg)

            # send email if sms fail
            if not skip_email and not did_send_sms:
                return self.send_email(
                    subject=title,
                    from_email=from_email,
                    text_content=msg,
                    template=template,
                    context=data,
                )

            return did_send_sms

    def send_email(
        self, subject, from_email, text_content, template=None, context=None
    ):
        try:
            subject, from_email, to = subject, from_email, self.user.email
            msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
            if template:
                html_content = get_template(template).render(
                    {
                        "order_id": context.get("order_id"),
                        "title": context.get("title") or subject,
                        "message": context.get("message") or text_content,
                    },
                )

                msg.attach_alternative(html_content, "text/html")
            msg.send()
            return True
        except:
            return False

    @property
    def is_delivery_person(self):
        return hasattr(self, "delivery_person")

    def clean_phone_number(self, phone_number: str):
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
        ("transfer", "transfer"),
        ("refund", "refund"),
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
        max_digits=12,
        default=0,
        decimal_places=2,
        editable=False,
    )
    transfer_fee = models.DecimalField(
        max_digits=12,
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
            ("unsettled", "unsettled"),
            ("settled", "settled"),
            ("on-hold", "on-hold"),
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

    def settle(self):
        if self.status == "unsettled":
            # check if the transaction has been unsettled for more than 24 hours
            now = timezone.now()
            if now > self.created_at + timezone.timedelta(hours=24):
                # settle the transaction
                self.status = "settled"
                self.save()

                # update wallet balance
                self.wallet.balance += self.amount
                self.wallet.save()


class Wallet(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    currency = models.CharField(max_length=4, default="NGN")
    balance = models.DecimalField(
        max_digits=12,
        null=True,
        default=00.00,
        decimal_places=2,
        blank=True,
        editable=False,
    )
    hide_balance = models.BooleanField(default=False)
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

    def get_unsettled_balance(self):
        # e.g if the user has 2 unsettled transactions of 100 and 200 respectively
        # the unsettled balance will be 300
        current_unsettled_balance = Decimal(0.00)
        all_unsettled_transactions = Transaction.objects.filter(
            wallet=self, status="unsettled"
        )
        # loop through all unsettled transactions and add all amounts of each unsettled transaction
        for unsettled_transaction in all_unsettled_transactions:
            current_unsettled_balance += unsettled_transaction.amount

        return current_unsettled_balance

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
    def get_transactions(self):
        return Transaction.objects.filter(wallet=self)

    # add balance to user's wallet
    def add_balance(
        self, amount: Decimal, title=None, desc=None, order: Order | None = None
    ):
        amount = Decimal(amount)
        title = "Wallet Credited" if not title else title
        desc = f"{amount} {self.currency} was added to wallet" if not desc else desc

        if not order:
            # convert the amount to decimal
            self.balance += amount
            self.save()
        else:
            # check if the wallet has a transaction for the order
            order_transaction = self.get_transactions().filter(order=order).first()
            if order_transaction:
                raise Exception("Order already has a transaction")

        # create a transaction
        transaction = Transaction.objects.create(
            wallet=self,
            title=title,
            status="success" if not order else "unsettled",
            desc=desc,
            amount=amount,
            order=order,
            _type="credit",
        )
        transaction.save()

    def deduct_balance(self, **kwargs):
        amount = kwargs.get("amount")
        transfer_fee = kwargs.get("transfer_fee", 0.00)
        transfer_fee = Decimal(transfer_fee)
        title = kwargs.get("title", "Wallet Debited")
        desc = kwargs.get(
            "desc", f"{self.currency} {amount} was deducted from your wallet"
        )
        transaction_id = kwargs.get("transaction_id", None)
        order = kwargs.get("order", None)
        status = kwargs.get("status", "pending")
        _type = kwargs.get("_type", "debit")
        transaction = None
        amount = Decimal(amount)
        transfer_fee = Decimal(transfer_fee)

        total_amount = amount + transfer_fee

        if not amount:
            raise Exception("Amount is required")

        if not transaction_id and not order:
            raise Exception("Transaction ID is required, or Order is required")

        if order:
            # handle order refund logic
            order_transaction = self.get_transactions().filter(order=order).first()

            if not order_transaction:
                raise Exception("Order does not have a transaction")

            if order_transaction.status in ["settled", "success"]:
                # debit the wallet
                self.balance -= total_amount
                self.save()

            # update the order transaction
            order_transaction.amount = total_amount
            order_transaction.status = "success"
            order_transaction._type = _type
            order_transaction.save()

            return order_transaction

        if transaction_id and order:
            raise Exception("Transaction ID and Order cannot be set at the same time")

        transaction_id = uuid.UUID(transaction_id)

        if self.balance < amount:
            raise Exception("Insufficient funds")

        # check if transaction exists
        transaction = self.get_transactions().get(
            transaction_id=transaction_id, _type="debit"
        )

        # debit the wallet
        self.balance -= total_amount
        self.save()

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

        transaction = (
            self.get_transactions().filter(transaction_id=transaction_id).first()
        )

        amount = Decimal(amount)

        # check if the transaction was successful
        if (
            transaction.status in ["success", "settled"]
            and transaction.amount == amount
        ):
            self.balance += amount
            self.save()

        if transaction is None:
            # create a transaction
            transaction = Transaction.objects.create(
                wallet=self,
                title=title,
                desc=desc,
                status="reversed",
                amount=amount,
                order=order,
                _type="debit",
            )
        transaction.title = title
        transaction.desc = desc
        transaction.save()
        return transaction

    # put transaction on hold
    def put_transaction_on_hold(self, transaction_id: str = None, order: Order = None):
        # transaction_id and order cannot be set at the same time
        if transaction_id and order:
            raise Exception("Transaction ID and Order cannot be set at the same time")

        transaction: Transaction = None
        desc = "Transaction is on hold, please contact support"
        if transaction_id:
            transaction = self.get_transactions().get(transaction_id=transaction_id)
            desc = f"Transaction #{transaction_id} is on hold, please contact support"
        elif order:
            transaction = self.get_transactions().get(order=order)
            desc = f"Transaction for Order {order.get_order_display_id()} is on hold, please contact support"

        # check if transaction is settled or successfull
        if transaction.status in ["settled", "success"]:
            # deduct the wallet
            self.deduct_balance(
                amount=transaction.amount,
                title="Transaction on Hold",
                desc=desc,
                transaction_id=transaction.transaction_id,
                status="on-hold",
            )

        # update the transaction
        transaction.status = "on-hold"
        transaction.desc = desc
        transaction.save()

        return transaction


class StoreOpenHours(models.Model):
    store = models.ForeignKey("Store", on_delete=models.CASCADE)
    day = models.CharField(
        max_length=10, choices=settings.DAYS_OF_WEEK, null=True, blank=True
    )
    open_time = models.TimeField()
    close_time = models.TimeField()

    def __str__(self) -> str:
        return f"{self.store.store_name} - {self.day}"

    def save(self, *args, **kwargs):
        # Convert open_time and close_time to UTC before saving
        self.open_time = self._convert_to_utc(self.open_time)
        self.close_time = self._convert_to_utc(self.close_time)

        super().save(*args, **kwargs)

    def _convert_to_utc(self, time: str):
        # Convert the provided time to UTC
        if time is not None:
            time_cols = time.split(":")
            time = "{}:{}".format(time_cols[0], time_cols[1])
            time = datetime.strptime(time, "%H:%M").time()
            # Combine the time with today's date to get a datetime object
            datetime_obj = datetime.combine(datetime.today(), time)

            # Get the current time zone (assuming vendors provide their local time zone)
            current_timezone = timezone.get_current_timezone()

            # Convert the datetime to UTC
            utc_datetime = timezone.make_aware(
                datetime_obj, current_timezone
            ).astimezone(timezone.utc)

            # Extract the time from the UTC datetime
            utc_time = utc_datetime.time()

            return utc_time
        return None

    # get store's open hours
    def get_store_open_hours(store_id):
        return StoreOpenHours.objects.filter(store__id=store_id)

    # Check store's open status
    @classmethod
    def check_store_open_status(cls, store_id, timezone=None, current_day=None):
        now = datetime.now(tz=timezone) if timezone else datetime.now()
        current_day = now.strftime("%a") if not current_day else current_day

        try:
            store_open_hours = cls.get_store_open_hours(store_id)
        except cls.DoesNotExist:
            return {"isOpen": False, "message": "Store does not exist."}, 404

        today_opening_hours = next(
            (
                hour
                for hour in store_open_hours
                if hour.day and hour.day.lower() == current_day.lower()
            )
            or store_open_hours[0],
            None,
        )

        # check if the first day is None
        if len(store_open_hours) > 0 and store_open_hours[0].day is None:
            today_opening_hours = store_open_hours[0]

        if not today_opening_hours:
            return {"isOpen": False, "message": "We are closed today."}

        open_time = today_opening_hours.open_time
        close_time = today_opening_hours.close_time

        if now.time() < open_time:
            return {
                "isOpen": False,
                "message": f"Opens today by {open_time.strftime('%I:%M %p')}",
            }
        elif now.time() >= close_time:
            return {"isOpen": False, "message": "We have closed."}
        else:
            return {
                "isOpen": True,
                "message": f"Closes today by {close_time.strftime('%I:%M %p')}",
            }


class Store(models.Model):
    vendor = models.ForeignKey(Profile, on_delete=models.CASCADE)

    # store details
    store_name = models.CharField(max_length=100)
    store_nickname = models.CharField(max_length=50)
    store_type = models.CharField(max_length=20)
    store_categories = models.JSONField(default=list, blank=True)
    store_rank = models.FloatField(default=0, editable=False)
    has_physical_store = models.BooleanField(default=False)
    store_cover_image = models.ImageField(
        upload_to=store_cover_image_directory_path, null=True, blank=True
    )
    store_bio = models.CharField(null=True, blank=True, max_length=150)
    store_average_preparation_time = models.JSONField(default=dict, blank=True)

    # store location
    country = CountryField(blank=True, default="NG")
    state = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    primary_address = models.CharField(max_length=255, null=True, blank=True)
    street_name = models.CharField(max_length=50, null=True, blank=True)
    primary_address_lat = models.FloatField(null=True, blank=True)
    primary_address_lng = models.FloatField(null=True, blank=True)
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    campus = models.CharField(max_length=50, null=True, blank=True)
    timezone = models.CharField(max_length=50, null=True, blank=True)
    gender_preference = models.ForeignKey(
        Gender, on_delete=models.SET_NULL, null=True, blank=True
    )

    # contact details
    whatsapp_numbers = models.JSONField(
        default=list, null=True, blank=True, editable=False
    )
    instagram_handle = models.CharField(max_length=50, null=True, blank=True)
    twitter_handle = models.CharField(max_length=50, null=True, blank=True)
    facebook_handle = models.CharField(max_length=50, null=True, blank=True)

    is_approved = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=(
            ("offline", "offline"),
            ("online", "online"),
            ("suspended", "suspended"),
        ),
        default="online",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.store_nickname

    # check if store is open
    def get_is_open_data(self):

        # if settings.DEBUG == True:
        #     return True

        is_open_data = {
            "is_open": False,
            "open_soon": False,
            "close_soon": False,
            "open_next_day": False,
        }
        # Get the current time in the store's time zone
        current_datetime = timezone.now()

        if self.timezone:
            try:
                current_datetime = current_datetime.astimezone(
                    pytz.timezone(self.timezone)
                )
            except pytz.UnknownTimeZoneError:
                logging.exception(
                    f"Error: Invalid timezone '{self.timezone}'. Check and update if necessary."
                )
                return False

        # Get the abbreviated day of the week (e.g., "Mon", "Tue", etc.)
        current_day_abbrev = current_datetime.strftime("%a")

        # Get the store's open hours for the current day or the default open hours
        try:
            store_open_hours = self.storeopenhours_set.filter(
                models.Q(day=current_day_abbrev)
                | models.Q(day__isnull=True)
                | models.Q(day__exact="")
            ).first()
        except (AttributeError, ValueError):
            return is_open_data

        if not store_open_hours:
            return is_open_data

        # Convert the open and close time to the store's timezone (handle potential errors)
        try:
            open_time = store_open_hours.open_time
            close_time = store_open_hours.close_time
        except (AttributeError, ValueError):
            return is_open_data

        if self.timezone:
            try:
                open_datetime = datetime.combine(datetime.today(), open_time)
                close_datetime = datetime.combine(datetime.today(), close_time)
                open_datetime = open_datetime.astimezone(pytz.timezone(self.timezone))
                close_datetime = close_datetime.astimezone(pytz.timezone(self.timezone))
            except (pytz.UnknownTimeZoneError, ValueError):
                return is_open_data

        else:
            open_datetime = datetime.combine(datetime.today(), open_time)
            close_datetime = datetime.combine(datetime.today(), close_time)

        # Extract the time from the datetime
        open_time = open_datetime.time()
        close_time = close_datetime.time()

        # Handle midnight closure edge case
        if open_time == close_time:
            return is_open_data

        # Check if store is open
        if open_time <= current_datetime.time() < close_time:
            is_open_data["is_open"] = True

        # check if store will open soon in 30 minutes (remeber the types are datetime.time)
        if open_time > current_datetime.time():
            if (open_time.hour - current_datetime.hour) == 1 and (
                open_time.minute - current_datetime.minute
            ) <= 30:
                is_open_data["open_soon"] = True

        # check if store will close soon in 30 minutes
        if close_time > current_datetime.time():
            if (close_time.hour - current_datetime.hour) == 1 and (
                close_time.minute - current_datetime.minute
            ) <= 30:
                is_open_data["close_soon"] = True

        # check if store will open next day
        if open_time > current_datetime.time() and current_day_abbrev != "Sun":
            is_open_data["open_next_day"] = True

        return is_open_data

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

            if not self.store_nickname:
                self.store_nickname = slugify(self.store_name)
                self.save()

        if self.store_average_preparation_time:
            is_average_preparation_time_valid = (
                self.validate_store_average_preparation_time()
            )
            if not is_average_preparation_time_valid:
                raise Exception("Invalid Store Average Preparation Time")

        super().save(*args, **kwargs)

    # store's wallet
    @property
    def wallet(self):
        return Wallet.objects.filter(user=self.vendor).first()

    # is store a school store
    @property
    def is_school_store(self):
        return True if self.school else False

    # get store's open hours
    @property
    def store_open_hours(self):
        return StoreOpenHours.objects.filter(store=self)

    @property
    def orders(self):
        return Order.get_orders_by_store(store=self)

    def get_store_products(self):
        return Item.get_items_by_store(store=self)

    def update_product_qty(self, product_slug, product_cart_qty, action):
        product_qs = self.get_store_products().filter(product_slug=product_slug)
        if not product_qs.exists():
            return False
        product = product_qs.first()
        if action == "add":
            product.product_qty += product_cart_qty
            product.save()
        elif action == "remove":
            product.product_qty -= product_cart_qty
            product.save()
        else:
            raise Exception("Invalid action")

        return True

    def validate_store_average_preparation_time(self):
        store_average_preparation_time = self.store_average_preparation_time
        if not isinstance(store_average_preparation_time, dict):
            return False
        # get min and max
        min = store_average_preparation_time.get("min")
        max = store_average_preparation_time.get("max")

        if not isinstance(min, int) or not isinstance(max, int):
            return False
        if min < 0 or max < 0:
            return False

        # check if min is greater than max
        if min > max:
            return False

        return True

    def menus(self):
        return Menu.objects.filter(store=self)

    @property
    def store_menu(self):
        return [menu.name for menu in self.menus()]


class Menu(models.Model):
    position = models.IntegerField(default=0, editable=False)
    name = models.CharField(max_length=50)
    store = models.ForeignKey("users.Store", on_delete=models.CASCADE)
    type = models.ForeignKey(
        "product.ItemAttribute",
        on_delete=models.SET_NULL,
        related_name="menus",
        blank=True,
        null=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position"]

    def __str__(self):
        return self.name

    def get_menu_items(self):
        return Item.objects.filter(product_menu=self)


class Hostel(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, null=True, blank=True, unique=True)
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True)
    campus = models.CharField(max_length=50, null=True, blank=True)
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True)
    fields = models.ManyToManyField("HostelField", blank=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.slug:
            self.slug = slugify(self.name)
            self.save()

    @property
    def hostel_fields(self):
        return HostelField.objects.filter(school=self.school)


class Student(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    campus = models.CharField(max_length=50, null=True, blank=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.SET_NULL, null=True, blank=True)
    hostel_fields = models.JSONField(default=list, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    """
    hostel_fields = [
        {
        field_id: 1,
        value: "value"
        },
        ...
    ]
    """

    def __str__(self) -> str:
        return self.user.user.username

    # validate hostel fields on save
    def save(self, *args, **kwargs):
        if self.hostel_fields:
            self.validate_hostel_fields()
        super().save(*args, **kwargs)

    # validate hostel fields
    def validate_hostel_fields(self):
        hostel_fields = self.hostel_fields
        for field in hostel_fields:
            field_id = field.get("field_id")
            value = field.get("value")
            hostel_field = HostelField.objects.filter(id=field_id).first()
            if not hostel_field:
                raise Exception("Hostel field_id={} does not exist".format(field_id))
            if hostel_field:
                if hostel_field.field_type == "number":
                    if not value.isnumeric():
                        raise Exception(f"{hostel_field.name} must be a number")
                if hostel_field.field_type == "select":
                    options = hostel_field.get_options()
                    if not value in options:
                        raise Exception(f"{hostel_field.name} must be one of {options}")
                if hostel_field.field_type == "radio":
                    options = hostel_field.get_options()
                    if not value in options:
                        raise Exception(f"{hostel_field.name} must be one of {options}")
                if hostel_field.field_type == "checkbox":
                    options = hostel_field.get_options()
                    if not value in options:
                        raise Exception(f"{hostel_field.name} must be one of {options}")
                if hostel_field.field_type == "text":
                    if not value:
                        raise Exception(f"{hostel_field.name} is required")
                if hostel_field.field_type == "textarea":
                    if not value:
                        raise Exception(f"{hostel_field.name} is required")
                if hostel_field.field_type == "date":
                    if not value:
                        raise Exception(f"{hostel_field.name} is required")
                if hostel_field.field_type == "time":
                    if not value:
                        raise Exception(f"{hostel_field.name} is required")
                if hostel_field.field_type == "file":
                    if not value:
                        raise Exception(f"{hostel_field.name} is required")
                if hostel_field.field_type == "image":
                    if not value:
                        raise Exception(f"{hostel_field.name} is required")
                if hostel_field.field_type == "loop":
                    if not value:
                        raise Exception(f"{hostel_field.name} is required")

        return True


class DeliveryPerson(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, unique=True)
    status = models.CharField(
        max_length=20,
        choices=(
            ("offline", "offline"),
            ("online", "online"),
            ("suspended", "suspended"),
        ),
        default="online",
    )
    is_approved = models.BooleanField(default=False)

    def __str__(self) -> str:
        sent_delivery_notifications_count = self.get_notifications().count()
        return f"{self.profile.user.username} - {sent_delivery_notifications_count} notifications sent"

    @property
    def wallet(self):
        return Wallet.objects.filter(user=self.profile).first()

    class Meta:
        ordering = ["-is_approved", "-status"]
        verbose_name_plural = "Delivery People"

    @property
    def orders(self):
        return Order.get_orders_by_delivery_person(delivery_person=self)

    # get delivery person's notifications
    def get_notifications(self):
        """
        Get delivery person's sent notifications
        """
        return DeliveryNotification.objects.filter(delivery_person=self, status="sent")

    def get_is_on_delivery(self):
        active_orders_count = Order.get_active_orders_count_by_delivery_person(
            delivery_person=self
        )
        if active_orders_count > 4:
            return True
        return False

    def get_active_orders_count(self):
        return Order.get_active_orders_count_by_delivery_person(delivery_person=self)

    # method to check if a order is able to be delivered by a delivery person
    def can_deliver(self, order: Order):
        delivery_notifications = DeliveryNotification.objects.filter(
            delivery_person=self
        )

        if delivery_notifications.filter(order=order).exists():
            return False

        # check if the delivery notification is either pending, processing or sent
        if (
            delivery_notifications.filter(status="pending").exists()
            or delivery_notifications.filter(status="processing").exists()
        ):
            return False

        order_user: Profile = order.user

        delivery_person_profile = self.profile

        # check if the order user is same as the delivery person
        if order_user == delivery_person_profile:
            return False

        if self.get_is_on_delivery():
            return False

        # check if the delivery person is a vendor and is linked to the order
        if (
            delivery_person_profile.is_vendor
            and order.linked_stores.filter(vendor=delivery_person_profile).exists()
        ):
            return False

        # check if delivery person is already delivering this order
        if order.get_delivery_person(delivery_person_id=self.id):
            return False

        # handle if the delivery person is a student
        if delivery_person_profile.is_student:
            # has_passed_valid_vendor_check = False
            # handle if the order user is a vendor
            if order_user.is_vendor and (
                # check if the order user store is in the delivery person's school and campus
                (order_user.store.school != delivery_person_profile.student.school)
                and (order_user.store.campus != delivery_person_profile.student.campus)
            ):
                return False

            # handle if the order user is a student
            if order_user.is_student:
                order_user_gender = order_user.gender
                delivery_person_gender = delivery_person_profile.gender

                if order_user_gender != delivery_person_gender:
                    return False

                # check if the delivery person is not in the same school and campus as the order user
                if (
                    delivery_person_profile.student.school != order_user.student.school
                    and delivery_person_profile.student.campus
                    != order_user.student.campus
                ):
                    return False
        else:
            # check if the delivery person is not in the same country as the order user
            if delivery_person_profile.country != order_user.country:
                print("check 9")
                return False

            # check if the delivery person is not in the same state as the order user
            if delivery_person_profile.state != order_user.state:
                print("check 10")
                return False

            # check if the delivery person is not in the same city as the order user
            if delivery_person_profile.city != order_user.city:
                print("check 11")
                return False

        return True

    # method to get delivery people that can deliver a order
    @staticmethod
    def get_delivery_people_that_can_deliver(order: Order):
        order_user: Profile = order.user
        delivery_people = DeliveryPerson.objects.filter(
            status="online",
            is_approved=True,
            profile__country=order_user.country,
        )
        delivery_people_that_can_deliver = []
        for delivery_person in delivery_people:
            if delivery_person.can_deliver(order):
                delivery_people_that_can_deliver.append(delivery_person)
        return delivery_people_that_can_deliver

    # send delivery request to delivery person
    @staticmethod
    def send_delivery(order: Order, store: Store):
        order_user: Profile = order.user
        delivery_people = DeliveryPerson.objects.filter(
            status="online",
            is_approved=True,
            profile__country=order_user.country,
        )
        did_complete = False
        did_find_delivery_person = False
        for delivery_person in delivery_people:
            # check if the delivery person has rejected the order before
            if delivery_person and delivery_person.can_deliver(order):
                # send new delivery request to queue
                queue_data = {
                    "order_id": order.order_track_id,
                    "delivery_person_id": delivery_person.id,
                }
                new_delivery_notification = DeliveryNotification.objects.create(
                    order=order,
                    store=store,
                    delivery_person=delivery_person,
                    status="pending",
                )
                new_delivery_notification.save()
                # send notification to queue
                had_error = send_notification_to_queue(
                    message=queue_data, queue_name="new-delivery-request"
                )
                did_complete = had_error == False
                did_find_delivery_person = True
                break  # break the loop if a delivery person is found

        if not did_find_delivery_person:
            # update the store status to no delivery person
            order.update_store_status(store_id=store.id, status="no-delivery-person")
            user: Profile = order.user
            order.notify_store(
                store_id=store.id,
                title="No Delivery Person",
                message="No delivery person was found available to deliver {}'s order {}, please tell the customer about this".format(
                    user.user.username, order.get_order_display_id()
                ),
            )
            did_complete = True

        return did_complete


class DeliveryNotification(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    delivery_person = models.ForeignKey(DeliveryPerson, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=(
            ("pending", "pending"),
            ("processing", "processing"),
            ("sent", "sent"),
            ("accepted", "accepted"),
            ("rejected", "rejected"),
            ("expired", "expired"),
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # add unique constraint to order and delivery person
    class Meta:
        unique_together = ("order", "delivery_person")

    # has_expired: this will check if the status is sent and the updated_at and the current time is greater than 1 minute
    @property
    def has_expired(self):
        if self.status == "sent":
            now = timezone.now()
            if now > self.updated_at + timezone.timedelta(minutes=1):
                # update status to expired
                self.status = "expired"
                self.save()
                return True
        return False


class UserActivity(models.Model):
    ACTIVITY_TYPES = (
        ("view", "view"),
        ("added_to_cart", "added_to_cart"),
        ("purchased", "purchased"),
        ("add_to_items", "add_to_items"),
        ("remove_from_order", "remove_from_order"),
        ("add_to_order", "add_to_order"),
        ("remove_from_items", "remove_from_items"),
    )
    user_id = models.PositiveIntegerField()
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_id} - {self.item.product_slug} - {self.timestamp}"

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "User Activities"

    @property
    def item_idx(self):
        return self.item.id


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


@receiver(models.signals.post_delete, sender=Profile)
def remove_file_from_s3(sender, instance, using, **kwargs):
    try:
        instance.image.delete(save=False)
    except:
        pass


# SIGNAL to send delivery when delivery notification is rejected or expired and store does not have a delivery person order.store_delivery_person(store_id) == None
@receiver(post_save, sender=DeliveryNotification)
def send_delivery_when_rejected_or_expired(
    sender, instance: DeliveryNotification, created, **kwargs
):
    if not created and instance and instance.status in ["rejected", "expired"]:
        order = instance.order
        store = instance.store
        # check if store has a delivery person
        does_store_have_delivery_person = (
            order.store_delivery_person(store_id=store.id) != None
        )
        if not does_store_have_delivery_person:
            # check if there are more delivery people for the order
            delivery_people = DeliveryPerson.get_delivery_people_that_can_deliver(
                order=order
            )  # get delivery people that can deliver the order
            if delivery_people and len(delivery_people) > 0:
                # send new delivery request to queue
                DeliveryPerson.send_delivery(order=order, store=store)
            else:  # if there are no delivery people that can deliver the order
                # update the store status to no delivery person
                order.update_store_status(
                    store_id=store.id, status="no-delivery-person"
                )
                # TODO send push notification to user and store
                user: Profile = order.user

                order.notify_store(
                    store_id=store.id,
                    title="No Delivery Person",
                    message="No delivery person was found available to deliver {}'s order {}, please tell the customer about this".format(
                        user.user.username, order.get_order_display_id()
                    ),
                )


@receiver(post_save, sender=Profile)
def update_profile_calling_code(sender, instance, created, **kwargs):
    # check if the calling code is already set
    if instance.country and not instance.calling_code:
        instance.has_calling_code()
        instance.save()


# signal to add others as store default menu when created
@receiver(post_save, sender=Store)
def add_others_as_default_menu(sender, instance, created, **kwargs):
    if created:
        menu = Menu.objects.create(name="Others", store=instance)
        menu.save()
        instance.save()
