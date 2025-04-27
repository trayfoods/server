from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from users.models import (
    UserAccount,
    Profile,
    Wallet,
    Transaction,
    Store,
    DeliveryPerson,
    DeliveryNotification,
    UserActivity,
)
from product.models import Order, Item
from django.core.exceptions import ValidationError
import uuid


class UserAccountModelTests(TestCase):
    def setUp(self):
        self.user = UserAccount.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

    def test_user_creation(self):
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.user.email, "test@example.com")
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)

    def test_user_roles(self):
        # Initially should have CLIENT role
        self.assertEqual(self.user.roles, ["CLIENT"])


class ProfileModelTests(TestCase):
    def setUp(self):
        self.user = UserAccount.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.get(user=self.user)

    def test_profile_creation(self):
        self.assertEqual(self.profile.user, self.user)
        self.assertFalse(self.profile.phone_number_verified)
        self.assertFalse(self.profile.has_required_fields)

    def test_profile_phone_verification(self):
        result = self.profile.send_phone_number_verification_code("1234567890", "+234")
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["pin_id"])


class WalletModelTests(TestCase):
    def setUp(self):
        self.user = UserAccount.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.get(user=self.user)
        Wallet.objects.create(user=self.profile)
        self.wallet = Wallet.objects.get(user=self.profile)

    def test_wallet_creation(self):
        self.assertEqual(self.wallet.user, self.profile)
        self.assertEqual(self.wallet.currency, "NGN")
        self.assertEqual(self.wallet.balance, Decimal("0.00"))

    def test_add_balance(self):
        amount = Decimal("1000.00")
        self.wallet.add_balance(amount)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, amount)

    def test_deduct_balance(self):
        # First add some balance
        self.wallet.add_balance(Decimal("1000.00"))

        new_transaction = Transaction.objects.create(
            wallet=self.wallet,
            title="Test Debit Transaction",
            desc="Test Debit Description",
            amount=Decimal("500.00"),
            _type="debit",
        )

        # Then try to deduct
        transaction = self.wallet.deduct_balance(
            amount=Decimal("500.00"),
            title="Test Deduction",
            desc="Test Description",
            transaction_id=new_transaction.transaction_id,
        )

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("500.00"))
        self.assertEqual(transaction.status, "pending")

    def test_insufficient_balance(self):
        with self.assertRaises(Exception):
            self.wallet.deduct_balance(
                amount=Decimal("1000.00"),
                title="Test Deduction",
                desc="Test Description",
                transaction_id=str(uuid.uuid4()),
            )


class TransactionModelTests(TestCase):
    def setUp(self):
        self.user = UserAccount.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.get(user=self.user)
        Wallet.objects.create(user=self.profile)
        self.wallet = Wallet.objects.get(user=self.profile)

    def test_transaction_creation(self):
        transaction = Transaction.objects.create(
            wallet=self.wallet,
            title="Test Transaction",
            desc="Test Description",
            amount=Decimal("1000.00"),
            _type="credit",
        )

        self.assertEqual(transaction.wallet, self.wallet)
        self.assertEqual(transaction.amount, Decimal("1000.00"))
        self.assertEqual(transaction.status, "pending")

    def test_transaction_settlement(self):
        transaction = Transaction.objects.create(
            wallet=self.wallet,
            title="Test Transaction",
            desc="Test Description",
            amount=Decimal("1000.00"),
            _type="credit",
            status="unsettled",
        )

        transaction.settle()
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, "settled")
        self.assertIsNotNone(transaction.settlement_date)


class StoreModelTests(TestCase):
    def setUp(self):
        self.user = UserAccount.objects.create_user(
            username="testvendor", email="vendor@example.com", password="testpass123"
        )
        self.profile = Profile.objects.get(user=self.user)
        self.store = Store.objects.create(
            vendor=self.profile,
            store_name="Test Store",
            store_nickname="teststore",
            store_type="restaurant",
        )

    def test_store_creation(self):
        self.assertEqual(self.store.vendor, self.profile)
        self.assertEqual(self.store.store_name, "Test Store")
        self.assertFalse(self.store.is_approved)

    def test_store_wallet(self):
        wallet = self.store.wallet
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.user, self.profile)


class DeliveryPersonModelTests(TestCase):
    def setUp(self):
        self.user = UserAccount.objects.create_user(
            username="testdelivery",
            email="delivery@example.com",
            password="testpass123",
        )
        self.profile = Profile.objects.get(user=self.user)
        self.delivery_person = DeliveryPerson.objects.create(profile=self.profile)

    def test_delivery_person_creation(self):
        self.assertEqual(self.delivery_person.profile, self.profile)
        self.assertEqual(self.delivery_person.status, "online")
        self.assertFalse(self.delivery_person.is_approved)

    def test_delivery_person_wallet(self):
        wallet = self.delivery_person.wallet
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.user, self.profile)


class DeliveryNotificationModelTests(TestCase):
    def setUp(self):
        # Create user and profile
        self.user = UserAccount.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.get(user=self.user)

        # Create store
        self.store = Store.objects.create(
            vendor=self.profile,
            store_name="Test Store",
            store_nickname="teststore",
            store_type="restaurant",
        )

        # Create delivery person
        self.delivery_person = DeliveryPerson.objects.create(profile=self.profile)

        # Create order
        self.order = Order.objects.create(user=self.profile)

    def test_delivery_notification_creation(self):
        notification = DeliveryNotification.objects.create(
            order=self.order,
            store=self.store,
            delivery_person=self.delivery_person,
            status="pending",
        )

        self.assertEqual(notification.order, self.order)
        self.assertEqual(notification.store, self.store)
        self.assertEqual(notification.delivery_person, self.delivery_person)
        self.assertEqual(notification.status, "pending")


class UserActivityModelTests(TestCase):
    def setUp(self):
        self.user = UserAccount.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.user2 = UserAccount.objects.create_user(
            username="testuser2", email="test2@example.com", password="test2pass123"
        )
        self.profile = Profile.objects.get(user=self.user)
        self.profile2 = Profile.objects.get(user=self.user2)
        self.user2_store = Store.objects.create(vendor=self.profile2)

        # Create a test item
        self.item = Item.objects.create(
            product_name="Test Item",
            product_price=Decimal("1000.00"),
            product_creator=self.user2_store,
        )

    def test_user_activity_creation(self):
        activity = UserActivity.objects.create(
            user_id=self.user.id, item=self.item, activity_type="view"
        )

        self.assertEqual(activity.user_id, self.user.id)
        self.assertEqual(activity.item, self.item)
        self.assertEqual(activity.activity_type, "view")
