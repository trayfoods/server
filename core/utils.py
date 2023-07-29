import json

from django.http import HttpResponse
from product.models import Order
from users.models import Store


class ProcessPayment:
    """
    This class is used to process the payment based on the event type.
    """

    def __init__(self, event_type, event_data):
        self.event_type = event_type
        self.event_data = event_data
        self.response_data = {}

    def process_payment(self):
        print("event_type", self.event_type)
        if self.event_type == "charge.success":
            return self.charge_success()
        elif self.event_type == "transfer.success":
            return self.transfer_success()
        elif self.event_type == "transfer.failed":
            return self.transfer_failed()
        elif self.event_type == "invoice.create":
            return self.invoice_create()
        elif self.event_type == "invoice.update":
            return self.invoice_update()
        elif self.event_type == "invoice.payment_failed":
            return self.invoice_payment_failed()
        elif self.event_type == "invoice.payment_success":
            return self.invoice_payment_success()
        elif self.event_type == "subscription.create":
            return self.subscription_create()
        elif self.event_type == "subscription.disable":
            return self.subscription_disable()
        elif self.event_type == "subscription.enable":
            return self.subscription_enable()
        elif self.event_type == "subscription.failed":
            return self.subscription_failed()
        elif self.event_type == "subscription.success":
            return self.subscription_success()
        elif self.event_type == "subscription.update":
            return self.subscription_update()
        elif self.event_type == "transfer.reversed":
            return self.transfer_reversed()
        else:
            return HttpResponse("Invalid event type", status=400)

    def charge_success(self):
        # get the order_id from event_data
        order_id = self.event_data["reference"]
        order_payment_status = self.event_data["status"]
        order_payment_method = self.event_data["authorization"]["channel"]
        order_price = self.event_data["amount"] / 100
        order_price = float(order_price)

        # try to get the order from the database
        # if the order does not exist, return 404
        try:
            # get the order from the database
            order = Order.objects.get(order_track_id=order_id)
            order.order_payment_method = order_payment_method

            # get all the needed data to verify the payment
            stores = order.stores_infos
            stores = json.loads(stores)

            delivery_price = float(order.delivery_price)
            overall_price = float(order.overall_price) - delivery_price

            # calculate the total price of the stores
            # and compare it with the overall price
            stores_total_price = 0
            stores__ids__with_credits = []
            for store in stores:
                store_id = store["storeId"]
                price = store["total"]["price"]
                plate_price = store["total"]["platePrice"]
                total_price = price + plate_price
                stores__ids__with_credits.append(
                    {"id": store_id, "credit": total_price}
                )
                stores_total_price += total_price

            # if the stores_total_price is greater than the overall_price
            # then the order is not valid
            order_price = order_price - delivery_price
            if stores_total_price > overall_price or order_price != overall_price:
                order.order_payment_status = "failed"
                order.order_status = "cancelled"
                order.order_message = (
                    "This Order Was Not Valid, Please Contact The Support Team"
                )
                order.save()
                return HttpResponse("Payment failed", status=400)

            print("stores_total_price: ", stores_total_price)
            print("order_price: ", order_price)
            print("overall_price: ", overall_price - delivery_price)

            # remove 40% of the delivery_price
            delivery_price = delivery_price - (delivery_price * 0.4)

            if "success" in order_payment_status:
                stores_with_issues = []
                # update the balance of the stores
                for store in stores__ids__with_credits:
                    store_nickname = store["id"]
                    # get the store from the database
                    # and update its credit
                    store = Store.objects.filter(
                        store_nickname=store_nickname.strip()
                    ).filter()
                    if store.exists():
                        store.credit_wallet(
                            amount=float(store["credit"]),
                            description=f"Order Payment From {order.user.username} with order id {order.order_track_id} was successful",
                        )
                        store.save()
                    else:
                        stores_with_issues.append(store_id)
                print("stores_with_issues: ", stores_with_issues)
                # update the order payment status
                order.order_payment_status = order_payment_status
                order.order_payment_method = order_payment_method
                order.delivery_price = delivery_price
                order.save()

            return HttpResponse("Payment successful", status=200)
        except Order.DoesNotExist:
            return HttpResponse("Order does not exist", status=404)

    def transfer_success(self):
        pass

    def transfer_failed(self):
        pass

    def invoice_create(self):
        pass

    def invoice_update(self):
        pass

    def invoice_payment_failed(self):
        pass

    def invoice_payment_success(self):
        pass

    def subscription_create(self):
        pass

    def subscription_disable(self):
        pass

    def subscription_enable(self):
        pass

    def subscription_failed(self):
        pass

    def subscription_success(self):
        pass

    def subscription_update(self):
        pass

    def transfer_reversed(self):
        pass
