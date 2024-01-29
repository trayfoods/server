import unittest
from unittest.mock import MagicMock
from product.mutations import MarkOrderAsMutation
from product.models import Order, Store
from django.conf import settings


class MarkOrderAsMutationTestCase(unittest.TestCase):
    def setUp(self):
        self.mutation = MarkOrderAsMutation()
        self.info = MagicMock()
        self.order_id = "12345"
        self.action = "accepted"
        self.user = MagicMock()
        self.order = MagicMock()
        self.order.user = MagicMock()
        self.order.shipping = {}
        self.order.order_status = "pending"
        self.order.order_payment_status = False
        self.order.get_order_status.return_value = "pending"
        self.order.is_pickup.return_value = False
        self.order.stores_infos = []
        self.order.stores_status = []
        self.order.update_store_status.return_value = True
        self.order.log_activity.return_value = True
        self.order.store_refund_customer.return_value = True
        self.user.profile.store = MagicMock()
        self.user.profile.is_vendor = True
        self.user.profile.store.id = 1
        self.user.profile.send_sms = MagicMock()
        self.info.context.user = self.user
        self.order.notify_user = MagicMock()

    def test_mutate_with_invalid_order(self):
        Order.objects.filter.return_value.exists.return_value = False

        result = self.mutation.mutate(
            self.mutation, self.info, self.order_id, self.action
        )

        self.assertEqual(result.error, "Order does not exists")

    def test_mutate_with_unauthorized_user(self):
        Order.objects.filter.return_value.exists.return_value = True
        self.order.user.user = MagicMock()

        result = self.mutation.mutate(
            self.mutation, self.info, self.order_id, self.action
        )

        self.assertEqual(
            result.error, "You are not authorized to interact with this order"
        )

    def test_mutate_with_invalid_action(self):
        Order.objects.filter.return_value.exists.return_value = True
        self.order.user.user = self.user

        result = self.mutation.mutate(
            self.mutation, self.info, self.order_id, "invalid_action"
        )

        self.assertEqual(result.error, "Invalid action")

    def test_mutate_with_cancelled_order(self):
        Order.objects.filter.return_value.exists.return_value = True
        self.order.user.user = self.user
        self.order.order_status = "accepted"

        result = self.mutation.mutate(
            self.mutation, self.info, self.order_id, "cancelled"
        )

        self.assertEqual(
            result.error,
            "You cannot cancel this order because it has been marked as Accepted",
        )

    def test_mutate_with_accepted_action_as_user(self):
        Order.objects.filter.return_value.exists.return_value = True
        self.order.user.user = self.user
        self.order.order_status = "not-started"
        self.order.order_payment_status = False
        settings.FRONTEND_URL = "https://example.com"

        result = self.mutation.mutate(
            self.mutation, self.info, self.order_id, "accepted"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.success_msg, "Order 12345 has been accepted")
        self.order.save.assert_called_once()
        self.order.notify_user.assert_called_once_with(
            message="Order 12345 has been accepted, we will notify you when it has been picked up by a delivery person"
        )

    def test_mutate_with_accepted_action_as_vendor(self):
        Order.objects.filter.return_value.exists.return_value = True
        self.order.user.user = self.user
        self.order.order_status = "pending"
        self.order.stores_infos = [
            {"storeId": 1, "total": {"price": "10.00", "plate_price": "2.00"}}
        ]
        self.order.stores_status = [{"storeId": 1, "status": "pending"}]
        self.order.get_order_status.return_value = "pending"
        self.order.is_pickup.return_value = False
        self.order.update_store_status.return_value = True
        self.order.log_activity.return_value = True
        self.order.store_refund_customer.return_value = True
        self.user.profile.store.id = 1
        self.user.profile.store.store_name = "Store 1"
        settings.FRONTEND_URL = "https://example.com"

        result = self.mutation.mutate(
            self.mutation, self.info, self.order_id, "accepted"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.success_msg, "Order 12345 has been accepted")
        self.order.save.assert_called_once()
        self.order.notify_user.assert_called_once_with(
            message="Order 12345 has been accepted by Store 1, we will notify you when some has been picked up by delivery people"
        )
        self.order.log_activity.assert_called_once_with(
            title="Order Accepted",
            activity_type="order_accepted",
            description="Store 1 accepted the order",
        )
        self.order.update_store_status.assert_called_once_with(1, "accepted")
        self.order.store_refund_customer.assert_not_called()

    def test_mutate_with_rejected_action_as_vendor(self):
        Order.objects.filter.return_value.exists.return_value = True
        self.order.user.user = self.user
        self.order.order_status = "pending"
        self.order.stores_infos = [
            {"storeId": 1, "total": {"price": "10.00", "plate_price": "2.00"}}
        ]
        self.order.stores_status = [{"storeId": 1, "status": "pending"}]
        self.order.get_order_status.return_value = "pending"
        self.order.is_pickup.return_value = False
        self.order.update_store_status.return_value = True
        self.order.log_activity.return_value = True
        self.order.store_refund_customer.return_value = True
        self.user.profile.store.id = 1
        self.user.profile.store.store_name = "Store 1"
        settings.FRONTEND_URL = "https://example.com"

        result = self.mutation.mutate(
            self.mutation, self.info, self.order_id, "rejected"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.success_msg, "Order 12345 has been rejected")
        self.order.save.assert_called_once()
        self.order.notify_user.assert_called_once_with(
            message="The items from your order 12345 provided by Store 1 have been rejected."
        )
        self.order.log_activity.assert_called_once_with(
            title="Order Rejected",
            activity_type="order_rejected",
            description="Store 1 rejected the order",
        )
        self.order.update_store_status.assert_called_once_with(1, "rejected")
        self.order.store_refund_customer.assert_called_once()

    def test_mutate_with_cancelled_action_as_vendor(self):
        Order.objects.filter.return_value.exists.return_value = True
        self.order.user.user = self.user
        self.order.order_status = "accepted"

        result = self.mutation.mutate(
            self.mutation, self.info, self.order_id, "cancelled"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.success_msg, "Order 12345 has been cancelled")
        self.order.save.assert_called_once()
        self.order.log_activity.assert_not_called()
        self.order.update_store_status.assert_not_called()
        self.order.store_refund_customer.assert_not_called()

    def test_mutate_with_accepted_action_as_vendor_and_no_store_info(self):
        Order.objects.filter.return_value.exists.return_value = True
        self.order.user.user = self.user
        self.order.order_status = "pending"
        self.order.stores_infos = []
        self.order.stores_status = []
        self.user.profile.store.id = 1
        self.user.profile.store.store_name = "Store 1"

        result = self.mutation.mutate(
            self.mutation, self.info, self.order_id, "accepted"
        )

        self.assertEqual(
            result.error, "No store info found for this order, please contact support"
        )
        self.order.save.assert_not_called()
        self.order.log_activity.assert_not_called()
        self.order.update_store_status.assert_not_called()
        self.order.store_refund_customer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
