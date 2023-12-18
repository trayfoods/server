import unittest
from unittest.mock import MagicMock
from product.models import Order
from django.conf import settings


class OrderTestCase(unittest.TestCase):
    def setUp(self):
        self.order = Order()
        self.order.shipping = '{"address": "123 Main St", "bash": "Apt 4"}'
        self.order.order_track_id = "12345"

    def test_send_order_sms_to_delivery_people(self):
        delivery_people = [MagicMock(profile=MagicMock(send_sms=MagicMock()))]

        self.order.send_order_sms_to_delivery_people(delivery_people)

        for delivery_person in delivery_people:
            delivery_person.profile.send_sms.assert_called_once_with(
                "You have a new order to deliver.\nOrder ID: 12345\nOrder Address: 123 Main St / Apt 4\nClick on the link below to accept the order.{}".format(
                    f"{settings.FRONTEND_URL}/delivery/12345"
                )
            )


if __name__ == "__main__":
    unittest.main()
