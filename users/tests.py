from django.test import TestCase
from users.models import UserAccount as User, Wallet
from users.models import Store, Vendor


class TestUser(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpass"
        )
        self.profile = self.user.profile
        self.vendor = Vendor.objects.create(
            user=self.profile,
        )
        self.wallet = Wallet.objects.create(
            user=self.profile,
        )
        self.store = Store.objects.create(
            store_nickname="Test Store", vendor=self.vendor, wallet=self.wallet
        )
        if "vendor" in self.user.roles:
            self.user.profile.vendor = self.vendor
            self.user.profile.vendor.store = self.store
            self.user.profile.wallet = self.wallet
            self.user.profile.save()

    def test_user_profile(self):
        self.assertEqual(self.user.profile, self.profile)

    def test_user_store(self):
        self.assertEqual(self.user.profile.vendor.store, self.store)

    def test_user_wallet(self):
        self.assertEqual(self.user.profile.wallet, self.wallet)
