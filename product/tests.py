from django.test import TestCase
from users.models import DeliveryPerson
from product.models import Order
from users.tests import TestUser

class OrderModelTestCase(TestUser):
    def setUp(self):
        self.delivery_person = DeliveryPerson.objects.create(
            user=self.user,
            wallet=self.wallet,
        )
        self.order = Order.objects.create(
            order_payment_currency="USD",
            order_payment_method="paypal",
            order_payment_url="https://www.paystack.com",
            order_payment_status="pending",
            delivery_person=self.delivery_person,
            order_message="Test order message",
        )
        self.order.linked_stores.add(self.store)

    def test_linked_stores(self):
        self.assertEqual(self.order.linked_stores.count(), 1)
        self.assertEqual(self.order.linked_stores.first(), self.store)

    def test_order_payment_currency(self):
        self.assertEqual(self.order.order_payment_currency, "NGN")

    def test_order_payment_method(self):
        self.assertEqual(self.order.order_payment_method, "card")

    def test_order_payment_url(self):
        self.assertEqual(self.order.order_payment_url, "https://www.paystack.com")

    def test_order_payment_status(self):
        self.assertEqual(self.order.order_payment_status, "pending")

    def test_delivery_person(self):
        self.assertEqual(self.order.delivery_person, self.delivery_person)

    def test_order_message(self):
        self.assertEqual(self.order.order_message, "Test order message")
