from decimal import Decimal
import os
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.db import transaction as djtransac

import uuid
import pytz
import logging

from django.utils import timezone

from django.db import models

Q = models.Q

from django_countries.fields import CountryField
from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from django.template.defaultfilters import slugify
from django.db.models.signals import post_save
from users.signals import balance_updated
from trayapp.utils import image_resized, image_exists, termii_send_otp

from product.models import Item, Order

from datetime import datetime
from django.conf import settings

from trayapp.utils import send_message_to_queue
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

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
        if self.image and (not self.pk or self.image_has_changed()):
            w, h = 300, 300  # Set the desired width and height for the resized image
            if image_exists(self.image.name):
                img_file, _, _, _ = image_resized(self.image, w, h)
                if img_file:
                    img_name = self.image.name
                    self.image.save(img_name, img_file, save=False)

        if self.phone_number:
            self.clean_phone_number(self.phone_number)

        super().save(*args, **kwargs)

    def image_has_changed(self):
        if not self.pk:
            return True
        old_image = Profile.objects.get(pk=self.pk).image
        return old_image != self.image

    def has_calling_code(self):
        calling_code = self.calling_code
        COUNTRY_CALLING_CODES = settings.COUNTRY_CALLING_CODES

        if not calling_code and self.country:
            country_code = self.country.code
            country_code_in_dict = COUNTRY_CALLING_CODES.get(country_code)

            if not country_code_in_dict:
                from restcountries import RestCountryApiV2 as rapi

                country = rapi.get_country_by_country_code(self.country.code)
                calling_code = country.calling_codes[0]
                COUNTRY_CALLING_CODES[country_code] = calling_code
            else:
                calling_code = country_code_in_dict

            self.calling_code = calling_code
            self.save()

        if "+" in calling_code:
            calling_code = calling_code.replace("+", "")
            self.calling_code = calling_code
            self.save()

        return bool(calling_code)

    def get_full_phone_number(self):
        return f"{self.calling_code}{self.phone_number}"

    def get_required_fields(self):
        required_fields = []

        if self.is_student:
            if not self.student.school:
                required_fields.append("school")
            if not self.student.campus:
                required_fields.append("campus")
            if not self.student.hostel:
                required_fields.append("hostel")
            if not self.student.hostel_fields:
                required_fields.append("hostelFields")
        else:
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

        if not required_fields:
            self.has_required_fields = True
            self.save()

        return required_fields

    @property
    def is_vendor(self):
        return self.store is not None

    @property
    def store(self):
        if not hasattr(self, "_store_cache"):
            self._store_cache = Store.objects.filter(vendor=self).first()
        return self._store_cache

    def get_wallet(self):
        if not hasattr(self, "_wallet_cache"):
            self._wallet_cache = Wallet.objects.filter(user=self).first()
        return self._wallet_cache

    def get_delivery_person(self):
        if not hasattr(self, "_delivery_person_cache"):
            self._delivery_person_cache = DeliveryPerson.objects.filter(
                profile=self
            ).first()
        return self._delivery_person_cache

    def clean_phone_number(self, phone_number: str):
        phone_number = phone_number.strip().replace(" ", "")
        user_with_phone = Profile.objects.filter(phone_number=phone_number).exclude(
            user=self.user
        )
        if user_with_phone.exists():
            raise Exception("Phone number already in use")

    @property
    def is_student(self):
        return hasattr(self, "student")

    def send_phone_number_verification_code(self, new_phone_number, calling_code):
        if settings.DEBUG or not settings.SMS_ENABLED:
            return {"success": True, "pin_id": "1234"}
        new_phone_number = new_phone_number.strip()

        # check if the phone number has been used by another user
        self.clean_phone_number(new_phone_number)

        new_phone_number = f"{calling_code}{new_phone_number}"

        verification = termii_send_otp(to=new_phone_number)

        pin_id = verification.get("pinId")

        success = True if pin_id else False

        if success:
            self.phone_number = new_phone_number.replace(calling_code, "")
            self.phone_number_verified = False
            self.save()

        return {
            "success": success,
            "pin_id": pin_id,
        }

    def verify_phone_number(self, pin_id, pin):
        import requests

        url = "https://v3.api.termii.com/api/sms/otp/verify"
        payload = {
            "api_key": settings.TERMII_API_KEY,
            "pin_id": pin_id,
            "pin": pin,
        }
        headers = {
            "Content-Type": "application/json",
        }
        response = requests.request("POST", url, headers=headers, json=payload)
        response = response.json()
        verified = response.get("verified")

        success = True if verified else False

        if success:
            self.phone_number_verified = True
            self.save()

        return success

    def send_sms(self, message: str):
        try:
            if SMS_ENABLED and self.has_calling_code():
                phone_number = f"{self.calling_code}{self.phone_number}"

                """
                Example message body:
                {
                    "phone_number": "+2348123456789",
                    "message": "SMS Message",
                    "channel": "dnd",
                    "type": "plain",
                    "from": "TrayFoods"
                }
                """
                queue_data = {
                    "phone_number": phone_number,
                    "message": message,
                    "channel": "dnd",
                    "type": "plain",
                    "from": "N-Alert",
                }
                return send_message_to_queue(
                    message=queue_data, queue_name="new-sms-notification"
                )

            if not SMS_ENABLED:
                logging.error("SMS is disabled")
                print(message)
                logging.info("End of SMS is disabled")
                return False if not settings.DEBUG else True

        except Exception as e:
            logging.exception(e)
            return False

    def send_push_notification(self, title, message, data=None):
        user = self.user
        if not user.has_token_device:
            return False

        user_devices = UserDevice.objects.filter(user=user, is_active=True).values_list(
            "device_token", flat=True
        )
        device_tokens = list(user_devices)
        if not device_tokens or len(device_tokens) == 0:
            return False
        """
        Example message body:
        {
            "device_tokens": ["device_token_1", "device_token_2"],
            "title": "Notification Title",
            "message": "Notification Message",
            "data": {
                "key1": "value1",
                "key2": "value2"
            }
        }
        """
        queue_data = {
            "device_tokens": device_tokens,
            "title": title,
            "message": message,
            "data": data,
        }
        return send_message_to_queue(
            message=queue_data, queue_name="new-push-notification"
        )

    def notify_me(self, title, message, data=None, skip_email=False):
        # if not self.send_push_notification(title, message, data):
        did_send_sms = self.send_sms(message=message)
        from_email = settings.DEFAULT_FROM_EMAIL
        template = None
        if data:
            from_email = data.get("from_email", None) or from_email
            template = data.get("template", None)

        # send email if sms fail
        if not skip_email and not did_send_sms:
            return self.send_email(
                subject=title,
                from_email=from_email,
                text_content=message,
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
    settlement_date = models.DateTimeField(null=True, blank=True, editable=False)
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
        """
        Settle the transaction. Avoid calling `self.save()` here to prevent loops.
        """
        try:
            # Skip if already settled
            if self.status == "settled":
                return

            # Use select_related to avoid additional queries for wallet and user
            transaction_with_related = Transaction.objects.select_related(
                "wallet__user__user"
            ).get(pk=self.pk)

            # Update wallet balance and transaction status in a single atomic transaction
            with djtransac.atomic():
                # Update wallet balance
                Wallet.objects.filter(pk=transaction_with_related.wallet.pk).update(
                    balance=models.F("balance") + transaction_with_related.amount
                )

                # Update transaction status
                Transaction.objects.filter(pk=self.pk).update(
                    status="settled", settlement_date=timezone.now()
                )

                # Send notification after successful updates
                transaction_with_related.wallet.user.notify_me(
                    title="Transaction Settled",
                    message=f"Transaction #{self.transaction_id} settled.",
                    data={"amount": self.amount},
                )

        except Exception as e:
            # Log or re-raise a specific error
            raise ValidationError(f"Settlement failed: {str(e)}")

    def settle_x(self):
        if self.status == "unsettled":
            now = timezone.now()
            if now > self.created_at:
                # Update both transaction and wallet in a single atomic transaction
                with djtransac.atomic():
                    # Update transaction status
                    Transaction.objects.filter(pk=self.pk).update(
                        status="settled", settlement_date=now
                    )
                    # Update wallet balance using F expression
                    Wallet.objects.filter(pk=self.wallet.pk).update(
                        balance=models.F("balance") + self.amount
                    )


@receiver(post_save, sender=Transaction)
def handle_transaction_settlement(sender, instance: Transaction, created, **kwargs):
    """
    Trigger settlement when status changes to "settled".
    Uses atomic transactions and error handling.
    """
    try:
        with djtransac.atomic():
            # Skip if this is a new instance created with "settled" status
            if created and instance.status == "settled":
                instance.settle()
                return

            # For updates, check if status changed to "settled"
            if not created:
                # Use select_for_update to prevent race conditions
                current_instance = Transaction.objects.select_for_update().get(
                    pk=instance.pk
                )
                if (
                    current_instance.status != "settled"
                    and instance.status == "unsettled"
                ):
                    instance.settle()

    except Transaction.DoesNotExist:
        logger.warning(
            f"Transaction {instance.transaction_id} no longer exists after save."
        )
    except Exception as e:
        logger.error(
            f"Failed to settle transaction {instance.transaction_id}: {str(e)}"
        )


@receiver(post_save, sender=Transaction)
def set_settlement_date(sender, instance, created, **kwargs):
    if created:
        # Use update instead of save to prevent recursive signal calls
        settlement_date = (
            instance.created_at + timezone.timedelta(days=1)
            if instance.status == "unsettled"
            else instance.created_at
        )
        Transaction.objects.filter(pk=instance.pk).update(
            settlement_date=settlement_date
        )


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
        _("passcode"), max_length=128, editable=False, default=make_password("0000")
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
        # Use aggregation instead of looping through transactions
        return Transaction.objects.filter(wallet=self, status="unsettled").aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")

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
    def add_balance(self, amount: Decimal, title=None, desc=None, order=None):
        amount = Decimal(amount)
        title = "Wallet Credited" if not title else title
        desc = f"{amount} {self.currency} was added to wallet" if not desc else desc

        with djtransac.atomic():
            if order:
                # Check for existing order transaction efficiently
                if Transaction.objects.filter(wallet=self, order=order).exists():
                    raise Exception("Order already has a transaction")
            else:
                # Update balance using F expression
                Wallet.objects.filter(pk=self.pk).update(
                    balance=models.F("balance") + amount
                )
                # Refresh from db to get updated balance
                self.refresh_from_db()

            # Create transaction in the same atomic block
            new_transaction = Transaction.objects.create(
                wallet=self,
                title=title,
                status="success" if not order else "unsettled",
                desc=desc,
                amount=amount,
                order=order,
                _type="credit",
            )

            # Notify user
            self.user.notify_me(
                title=title,
                message=desc,
                data={"order_id": order.get_order_display_id() if order else None},
            )

            return new_transaction

    def deduct_balance(self, **kwargs):
        amount = Decimal(kwargs.get("amount"))
        transfer_fee = Decimal(kwargs.get("transfer_fee", 0.00))
        title = kwargs.get("title", "Wallet Debited")
        desc = kwargs.get(
            "desc", f"{self.currency} {amount} was deducted from your wallet"
        )
        transaction_id = kwargs.get("transaction_id")
        order = kwargs.get("order")
        status = kwargs.get("status", "pending")
        _type = kwargs.get("_type", "debit")

        if not amount:
            raise Exception("Amount is required")

        if not transaction_id and not order:
            raise Exception("Transaction ID is required, or Order is required")

        if transaction_id and order:
            raise Exception("Transaction ID and Order cannot be set at the same time")

        total_amount = amount + transfer_fee

        with djtransac.atomic():
            # Lock the wallet row for update
            wallet = Wallet.objects.select_for_update().get(pk=self.pk)

            if order:
                # Handle order refund logic
                order_transaction = (
                    Transaction.objects.select_for_update()
                    .filter(wallet=self, order=order)
                    .first()
                )

                if not order_transaction:
                    raise Exception("Order does not have a transaction")

                if order_transaction.status in ["settled", "success"]:
                    # Update balance using F expression
                    Wallet.objects.filter(pk=self.pk).update(
                        balance=models.F("balance") - total_amount
                    )
                    self.refresh_from_db()

                    # Update the order transaction
                    Transaction.objects.filter(pk=order_transaction.pk).update(
                        amount=total_amount, status="success", _type=_type
                    )
                    order_transaction.refresh_from_db()
                    transaction_result = order_transaction

            else:
                # Handle transaction_id case
                # transaction_id = uuid.UUID(transaction_id)

                if wallet.balance < amount:
                    raise Exception("Insufficient funds")

                # Update balance and get transaction in one atomic operation
                Wallet.objects.filter(pk=self.pk).update(
                    balance=models.F("balance") - total_amount
                )
                self.refresh_from_db()

                transaction_result = Transaction.objects.select_for_update().get(
                    wallet=self, transaction_id=transaction_id, _type="debit"
                )

                Transaction.objects.filter(pk=transaction_result.pk).update(
                    title=title, order=order, desc=desc, status=status
                )
                transaction_result.refresh_from_db()

            # Notify user
            self.user.notify_me(
                title=title,
                message=desc,
                data={"order_id": order.get_order_display_id() if order else None},
            )

            return transaction_result

    def reverse_transaction(self, **kwargs):
        amount = Decimal(kwargs.get("amount"))
        title = kwargs.get("title", "Transfer Reversed")
        order = kwargs.get("order")
        transaction_id = kwargs.get("transaction_id")

        currency_symbol = "₦" if self.currency == "NGN" else None
        currency = self.currency if currency_symbol is None else ""
        desc = kwargs.get(
            "desc", f"{currency_symbol}{amount} {currency} was reversed to your wallet"
        )

        with djtransac.atomic():
            # Lock the wallet for update
            wallet = Wallet.objects.select_for_update().get(pk=self.pk)

            if transaction_id:
                # Get and lock the transaction
                transaction_obj = (
                    Transaction.objects.select_for_update()
                    .filter(wallet=self, transaction_id=transaction_id)
                    .first()
                )

                if (
                    transaction_obj
                    and transaction_obj.status in ["success", "settled"]
                    and transaction_obj.amount == amount
                ):
                    # Update wallet balance atomically
                    Wallet.objects.filter(pk=self.pk).update(
                        balance=models.F("balance") + amount
                    )
                    wallet.refresh_from_db()

            # Create or update transaction
            if transaction_id and not transaction_obj:
                transaction_obj = Transaction.objects.create(
                    wallet=self,
                    title=title,
                    desc=desc,
                    status="reversed",
                    amount=amount,
                    order=order,
                    _type="debit",
                )
            elif transaction_obj:
                Transaction.objects.filter(pk=transaction_obj.pk).update(
                    title=title, desc=desc, status="reversed"
                )
                transaction_obj.refresh_from_db()

            # Notify user
            self.user.notify_me(
                title=title,
                message=desc,
                data={"order_id": order.get_order_display_id() if order else None},
            )

            return transaction_obj

    def put_transaction_on_hold(self, transaction_id: str = None, order: Order = None):
        if transaction_id and order:
            raise Exception("Transaction ID and Order cannot be set at the same time")

        with djtransac.atomic():
            # Lock the wallet for update
            wallet = Wallet.objects.select_for_update().get(pk=self.pk)

            # Prepare query for transaction lookup
            transaction_query = {"wallet": self}
            if transaction_id:
                transaction_query["transaction_id"] = transaction_id
                desc = (
                    f"Transaction #{transaction_id} is on hold, please contact support"
                )
            elif order:
                transaction_query["order"] = order
                desc = f"Transaction for Order {order.get_order_display_id()} is on hold, please contact support"
            else:
                desc = "Transaction is on hold, please contact support"

            # Get and lock the transaction
            transaction_obj = Transaction.objects.select_for_update().get(
                **transaction_query
            )

            if transaction_obj.status in ["settled", "success"]:
                # Deduct balance atomically
                Wallet.objects.filter(pk=self.pk).update(
                    balance=models.F("balance") - transaction_obj.amount
                )
                wallet.refresh_from_db()

            # Update transaction status
            Transaction.objects.filter(pk=transaction_obj.pk).update(
                status="on-hold", desc=desc
            )
            transaction_obj.refresh_from_db()

            return transaction_obj

    def send_wallet_alert(self, amount: Decimal):
        """
        Send a wallet alert to the user
        e.g
        ```
        wallet = Wallet.objects.get(user__username="divine")
        wallet.send_wallet_alert(1000)
        ```
        """
        # check if the user has a device
        message = (
            f"{amount} {self.currency} has been credited to your wallet main balance"
            if amount > 0
            else f"{amount} {self.currency} has been deducted from your wallet"
        )
        # if self.user.user.has_token_device:
        #     # send a push notification
        #     title = "Credit Alert" if amount > 0 else "Debit Alert"
        #     self.user.send_push_notification(title, message)
        # else:
        # send an SMS
        self.user.send_sms(message)


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

    @classmethod
    def filter_by_country(cls, country):
        return cls.objects.filter(country=country)

    @classmethod
    def filter_by_state(cls, state):
        state = state.lower()
        return cls.objects.filter(state=state)

    @classmethod
    def filter_by_city(cls, city):
        city = city.lower()
        return cls.objects.filter(city=city)

    @classmethod
    def filter_by_school(cls, school):
        school = school.lower()
        return cls.objects.filter(school=school)

    @classmethod
    def filter_by_campus(cls, campus):
        campus = campus.lower()
        return cls.objects.filter(campus=campus)

    # check if store is open
    # e.g 10:00 AM - 8:00 PM is 10:00:00 - 20:00:00
    def get_is_open_data(self):
        is_open_data = {
            "is_open": False,
            "open_soon": False,
            "close_soon": False,
            "open_next_day": False,
            "message": "We are closed for today, please come back tomorrow.",
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
                return is_open_data

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
                open_datetime = datetime.combine(current_datetime.date(), open_time)
                close_datetime = datetime.combine(current_datetime.date(), close_time)
                open_datetime = pytz.timezone(self.timezone).localize(open_datetime)
                close_datetime = pytz.timezone(self.timezone).localize(close_datetime)
            except (pytz.UnknownTimeZoneError, ValueError):
                return is_open_data
        else:
            open_datetime = timezone.make_aware(
                datetime.combine(current_datetime.date(), open_time),
                current_datetime.tzinfo,
            )
            close_datetime = timezone.make_aware(
                datetime.combine(current_datetime.date(), close_time),
                current_datetime.tzinfo,
            )

        # Check if store is open
        if open_datetime <= current_datetime < close_datetime:
            is_open_data["is_open"] = True
            is_open_data["message"] = None

        # Check if store will close soon
        if open_datetime <= current_datetime < close_datetime:
            time_to_close = (close_datetime - current_datetime).total_seconds()
            if 0 < time_to_close <= 1800:  # 30 minutes
                is_open_data["close_soon"] = True
                is_open_data["message"] = (
                    f"Closes today by {close_datetime.strftime('%I:%M %p')}"
                )

        # Check if store will open next day
        if current_datetime >= close_datetime:
            is_open_data["open_next_day"] = True
            is_open_data["message"] = (
                "We are closed for today, please come back tomorrow."
            )
        # Check if store will open soon
        if current_datetime < open_datetime:
            time_to_open = (open_datetime - current_datetime).total_seconds()
            if 0 < time_to_open <= 1800:  # 30 minutes or less
                is_open_data["open_soon"] = True
                # message should be like "Opening soon by 10:00 AM in about 30 minutes"
                is_open_data["message"] = (
                    f"Opening soon by {open_datetime.strftime('%I:%M %p')} in about {time_to_open // 60} minutes"
                )
            else:
                is_open_data["message"] = (
                    f"Opens today by {open_datetime.strftime('%I:%M %p')}"
                )

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
        return [menu.name.strip() for menu in self.menus()]

    # check if store can accept orders
    def can_accept_orders(self):
        return (
            # check if store is online
            self.status == "online"
            # check if store is approved
            and self.is_approved
            # check if store's vendor is active
            and self.vendor.user.is_active
            # check if store is open
            and self.get_is_open_data()["is_open"]
        ) or settings.DEBUG  # Allow store to accept orders in debug mode


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
    categories = models.ManyToManyField("product.ItemAttribute", blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position"]

    def __str__(self):
        return self.store.store_nickname + " - " + self.name

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
            try:
                self.slug = slugify(
                    self.name
                    + " "
                    + self.school.name
                    + " "
                    + self.gender.name
                )
                self.save()
            except:
                # use uuid
                self.slug = str(uuid.uuid4())[:6]
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
        return self.get_active_orders_count() > 4

    def get_active_orders_count(self):
        return Order.get_active_orders_count_by_delivery_person(delivery_person=self)

    # method to check if a order is able to be delivered by a delivery person
    def can_deliver(self, order: Order):
        if not self.profile.user.is_active:
            return False

        if DeliveryNotification.objects.filter(
            Q(delivery_person=self)
            & Q(
                order=order
            )  # check if the delivery person has already been sent a notification for the order
            | Q(
                delivery_person=self, status__in=["pending", "processing"]
            )  # check if the delivery person has a pending or processing notification
        ).exists():
            return False

        if order.user == self.profile:
            return False

        if self.get_is_on_delivery():
            return False

        if (
            self.profile.is_vendor
            and order.linked_stores.filter(vendor=self.profile).exists()
        ):
            return False

        if order.get_delivery_person(delivery_person_id=self.id):
            return False

        if self.profile.is_student:
            if order.user.is_vendor and (
                order.user.store.school != self.profile.student.school
                or order.user.store.campus != self.profile.student.campus
            ):
                return False

            if order.user.is_student:
                if order.user.gender != self.profile.gender:
                    return False

                if (
                    self.profile.student.school != order.user.student.school
                    or self.profile.student.campus != order.user.student.campus
                ):
                    return False
        else:
            if (
                self.profile.country != order.user.country
                or self.profile.state != order.user.state
                or self.profile.city != order.user.city
            ):
                return False

        return True

    # method to get delivery people that can deliver a order
    @staticmethod
    def get_delivery_people_that_can_deliver(order: Order):
        delivery_people = (
            DeliveryPerson.objects.filter(
                status="online",
                is_approved=True,
                profile__country=order.user.country,
            )
            .select_related("profile")
            .iterator()
        )

        return [dp for dp in delivery_people if dp.can_deliver(order)]

    # send delivery request to delivery person
    @staticmethod
    def send_delivery(order: Order, store: Store):
        delivery_people = (
            DeliveryPerson.objects.filter(
                status="online",
                is_approved=True,
                profile__country=order.user.country,
                profile__user__is_active=True,
            )
            .select_related("profile")
            .iterator()
        )

        for delivery_person in delivery_people:
            if delivery_person.can_deliver(order):
                DeliveryNotification.objects.create(
                    order=order,
                    store=store,
                    delivery_person=delivery_person,
                    status="pending",
                )
                queue_data = {
                    "order_id": order.order_track_id,
                    "delivery_person_id": delivery_person.id,
                }
                send_message_to_queue(
                    message=queue_data, queue_name="new-delivery-request"
                )
                return True

        order.update_store_status(store_id=store.id, status="no-delivery-person")
        order.notify_store(
            store_id=store.id,
            title="No Delivery Person",
            message=f"No delivery person was found available to deliver {order.user.user.username}'s order {order.get_order_display_id()}, please tell the customer about this",
        )
        return False


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
