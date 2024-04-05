import json

from django.http import HttpResponse
from product.models import Order
from users.models import Store, Transaction, DeliveryPerson
from trayapp.decorators import get_time_complexity
from decimal import Decimal

from django.conf import settings


class ProcessPayment:
    """
    This class is used to process the payment based on the event type.
    """

    def __init__(self, event_type, event_data):
        self.event_type = event_type
        self.event_data = event_data
        self.response_data = {}

    @get_time_complexity
    def process_payment(self):
        print("event_type", self.event_type)
        if self.event_type == "charge.success":
            return self.charge_success()
        elif self.event_type == "transfer.success":
            return self.transfer_success()
        elif self.event_type == "transfer.failed":
            return self.transfer_failed()
        elif self.event_type == "transfer.reversed":
            return self.transfer_reversed()
        elif self.event_type == "refund.failed":
            return self.refund_failed()
        elif self.event_type == "refund.processed":
            return self.refund_processed()
        elif self.event_type == "refund.pending":
            return HttpResponse("Refund pending", status=200)
        elif self.event_type == "refund.processing":
            return HttpResponse("Refund processing", status=200)
        else:
            return HttpResponse("Invalid event type", status=400)

    def charge_success(self):
        # get the values from event_data
        order_id = self.event_data["reference"]
        order_payment_status = self.event_data["status"]
        try:
            order_payment_method = self.event_data["authorization"]["channel"]
        except KeyError:
            order_payment_method = "unknown"

        order_price = self.event_data["amount"]
        order_gateway_fee = self.event_data.get("fees", 0)
        # convert the order_price to a decimal and divide it by 100
        order_price = Decimal(order_price) / 100

        # get the order from the database
        order_qs = Order.objects.filter(order_track_id=order_id).exclude(
            order_payment_status="success"
        )

        # check if the order exists
        if not order_qs.exists():
            return HttpResponse("Order does not exist", status=404)

        order = order_qs.first()
        order.order_payment_method = order_payment_method
        delivery_fee = Decimal(order.delivery_fee)
        overall_price = Decimal(order.overall_price)
        # calulate the payment gateway charges


        order_price = order_price - delivery_fee - Decimal(order.service_fee)

        if overall_price > order_price:
            order.order_payment_status = "pending-refund"
            order.order_status = "failed"
            order.save()
            order.notify_user(
                message="Payment for Order {} has failed, kindly contact support for your refund".format(
                    order.get_order_display_id()
                )
            )
            return HttpResponse("Payment failed, Processing Refund", status=400)

        if "success" == order_payment_status:
            # get 25% of the delivery fee
            delivery_fee_percentage = delivery_fee * Decimal(0.25)
            new_delivery_fee = delivery_fee - delivery_fee_percentage
            # update the order payment status
            order.order_payment_status = order_payment_status
            order.order_payment_method = order_payment_method
            order.delivery_fee_percentage = delivery_fee_percentage
            order.delivery_fee = new_delivery_fee
            order.order_gateway_fee = order_gateway_fee
            order.order_status = "processing"
            order.save()

            shipping_address = order.shipping
            shipping_address = shipping_address.get("address", None)

            # notify all stores that are involved in the order
            stores_infos = order.stores_infos
            for store_info in stores_infos:
                store_id = store_info.get("storeId")
                if not store_id:
                    continue

                store: Store = order.linked_stores.filter(id=int(store_id)).first()
                if store:
                    # deduct all the product_cart_qty from the product_qty
                    store_items = store_info["items"]
                    for item in store_items:
                        product_slug = item.get("product_slug")
                        product_cart_qty = item.get("product_cart_qty")
                        if product_slug and product_cart_qty:
                            store.update_product_qty(product_slug, product_cart_qty, "remove")

                    total = store_info["total"]
                    # get the store total normal price
                    store_total_price = total.get("price", 0)
                    # get the store plate price
                    store_plate_price = total.get("plate_price", 0)
                    # get the store option group price
                    store_option_groups_price = total.get("option_groups_price", 0)

                    overrall_store_price = (
                        Decimal(store_total_price)
                        + Decimal(store_plate_price)
                        + Decimal(store_option_groups_price)
                    )

                    store.vendor.notify_me(
                        title="New Order",
                        msg="New Order of {} {} was made, tap on this link to view the order → {}/checkout/{}".format(
                            order.order_currency,
                            overrall_store_price,
                            settings.FRONTEND_URL,
                            order.order_track_id,
                        ),
                    )

            if order.user:
                # notify the user
                order.notify_user(
                    title="Order Placed",
                    message="Order {} has been sent to the store, we will notify you when the store accept the order".format(
                        order.get_order_display_id()
                    ),
                )

        return HttpResponse("Payment successful", status=200)

    def transfer_success(self):
        amount = self.event_data["amount"]
        transaction_id = self.event_data["reference"]
        gateway_transfer_id = self.event_data["id"]
        transfer_status = self.event_data["status"]
        failures = self.event_data["failures"]

        if failures:
            return HttpResponse("Transfer failed", status=400)

        # get transaction from the database
        transaction = Transaction.objects.filter(transaction_id=transaction_id).first()

        if not transaction:
            return HttpResponse("Transaction does not exist", status=404)

        if amount:
            amount = Decimal(amount) / 100
        else:
            amount = transaction.amount

        if transaction.amount != amount:
            return HttpResponse("Invalid amount", status=400)

        # check if the transaction is already successful
        if transaction.status == "success":
            return HttpResponse("Transfer already successful", status=200)

        if "success" == transfer_status:
            account_name = self.event_data["recipient"]["name"]
            # deduct the amount_with_charges from the wallet
            kwargs = {
                "amount": amount,
                "transaction_id": transaction_id,
                "transfer_fee": transaction.transfer_fee,
                "desc": "TRF to " + account_name,
                "status": "success",
            }
            transaction.wallet.deduct_balance(**kwargs)

            if not transaction:
                return HttpResponse("Transfer failed", status=400)
            # update the transaction status
            transaction.status = "success"
            transaction.gateway_transfer_id = gateway_transfer_id
            transaction.save()
            return HttpResponse("Transfer successful", status=200)

        return HttpResponse("Transfer failed", status=400)

    def transfer_failed(self):
        amount = self.event_data["amount"]
        amount = Decimal(amount) / 100
        transaction_id = self.event_data["reference"]
        gateway_transfer_id = self.event_data["id"]
        transfer_status = self.event_data["status"]

        # get transaction from the database
        transaction = Transaction.objects.filter(transaction_id=transaction_id).first()

        if not transaction:
            return HttpResponse("Transaction does not exist", status=404)

        if transaction.amount != amount:
            return HttpResponse("Invalid amount", status=400)

        # check if the transaction is already failed
        if transaction.status == "failed":
            return HttpResponse("Transfer already failed", status=200)

        if "failed" == transfer_status:
            # update the transaction status
            transaction.status = "failed"
            transaction.gateway_transfer_id = gateway_transfer_id
            transaction.save()
            return HttpResponse("Transfer failed", status=200)

        return HttpResponse("Transfer failed", status=400)

    def transfer_reversed(self):
        amount = self.event_data["amount"]
        amount = Decimal(amount) / 100
        transaction_id = self.event_data["reference"]
        gateway_transfer_id = self.event_data["id"]
        transfer_status = self.event_data["status"]
        account_name = self.event_data["recipient"]["name"]

        # get transaction from the database
        transaction = Transaction.objects.filter(transaction_id=transaction_id).first()

        if not transaction:
            return HttpResponse("Transaction does not exist", status=404)

        if transaction.amount != amount:
            return HttpResponse("Invalid amount", status=400)

        # check if the transaction is already successful
        if transaction.status == "reversed":
            return HttpResponse("Transfer already Reversed", status=200)

        if "reversed" == transfer_status:
            # reverse the transaction
            kwargs = {
                "amount": amount,
                "transaction_id": transaction_id,
                "desc": "TRF to " + account_name + " was reversed to your wallet",
            }
            transaction.wallet.reverse_transaction(**kwargs)
            # update the transaction status
            transaction.status = "reversed"
            transaction.gateway_transfer_id = gateway_transfer_id
            transaction.save()
            return HttpResponse("Transfer Reversed", status=200)

        return HttpResponse("Transfer Process Failed", status=400)

    def refund_processed(self):
        print("refund_processed", self.event_data)
        """
        Refund has successfully been processed by the processor.
        """

        # get the values from event_data
        order_id = self.event_data.get("transaction_reference", None)
        order_price = self.event_data.get("amount", 0.00)

        # check if the order_id and order_price is not None
        if not order_id or not order_price:
            return HttpResponse("Invalid data", status=400)

        # convert the order_price to a decimal and divide it by 100
        order_price = Decimal(order_price) / 100

        order_qs = Order.objects.filter(
            order_track_id=order_id, order_payment_status="pending-refund"
        )

        if not order_qs.exists():
            print("order_qs", order_qs)
            return HttpResponse("Order does not exist", status=404)

        # get the order from the database
        order = Order.objects.get(
            order_track_id=order_id, order_payment_status="pending-refund"
        )

        print("order", order)

        # deduct the amount from all stores that are involved in the order
        stores_infos = order.stores_infos
        affected_stores = []
        for store_info in stores_infos:
            store_id = store_info.get("storeId")
            if not store_id:
                continue

            store_status = order.get_store_status(store_id)
            # get the store total normal price
            store_total_price = store_info["total"]["price"]
            # get the store plate price
            store_plate_price = store_info["total"]["plate_price"]

            store_option_groups_price = store_info["total"]["option_groups_price"]

            overrall_store_price = (
                Decimal(store_total_price)
                + Decimal(store_plate_price)
                + Decimal(store_option_groups_price)
            )
            if store_status == "pending-refund" and overrall_store_price == order_price:
                order.funds_refunded += order_price 
                store: Store = order.linked_stores.filter(id=int(store_id)).first()
                # check if the store status is "pending-refund"
                if store:
                    affected_stores.append(str(store.id))

                    store.wallet.deduct_balance(
                        amount=overrall_store_price,
                        desc="Refund for Order {}".format(order.get_order_display_id()),
                        order=order,
                    )

                    order.update_store_status(store_id=store.id, status="refunded")
                    # break the loop when one store has been refunded
                    break

        store_statuses = []
        # get all order store status
        for status in order.stores_status:
            # replace affected stores status with refunded
            if str(status["storeId"]) in affected_stores:
                status["status"] = "refunded"
                store_statuses.append(status)
            store_statuses.append(status["status"])

        # check if all the stores has refunded to the user
        if all(status == "refunded" for status in store_statuses):
            # update the order payment status
            order.order_payment_status = "refunded"
            order.save()
            # notify the user
            order.notify_user(
                title="Order Refunded",
                message="Order {} has been refunded".format(
                    order.get_order_display_id()
                )
            )

        # check if some stores has refunded to the user
        if any(status == "refunded" for status in store_statuses):
            # update the order payment status
            order.order_payment_status = "partially-refunded"
            order.save()
            # notify the user
            order.notify_user(
                title="Order Refunded",
                message="Order {} has been partially refunded".format(
                    order.get_order_display_id()
                )
            )

        return HttpResponse("Refund successful", status=200)

    def refund_failed(self):
        print("refund_failed", self.event_data)
        """
        Refund has failed to be processed by the processor.
        """

        # get the values from event_data
        order_id = self.event_data.get("transaction_reference", None)
        order_price = self.event_data.get("amount", None)

        # check if the order_id and order_price is not None
        if not order_id or not order_price:
            return HttpResponse("Invalid data", status=400)

        # convert the order_price to a decimal and divide it by 100
        order_price = Decimal(order_price) / 100

        if not Order.objects.filter(
            order_track_id=order_id, order_payment_status="pending-refund"
        ).exists():
            return HttpResponse("Order does not exist", status=404)

        # get the order from the database
        order = Order.objects.get(
            order_track_id=order_id, order_payment_status="pending-refund"
        )

        # deduct the amount from all stores that are involved in the order
        stores_infos = order.stores_infos
        affected_stores = []
        for store_info in stores_infos:
            store_id = store_info.get("storeId")
            if not store_id:
                continue

            store_status = order.get_store_status(store_id)
            # get the store total normal price
            store_total_price = store_info["total"]["price"]
            # get the store plate price
            store_plate_price = store_info["total"]["plate_price"]

            store_option_groups_price = store_info["total"]["option_groups_price"]

            overrall_store_price = (
                Decimal(store_total_price)
                + Decimal(store_plate_price)
                + Decimal(store_option_groups_price)
            )

            # check if the store status is "pending-refund"
            if store_status == "pending-refund" and overrall_store_price == order_price:
                print("store_id", store_id)
                store: Store = order.linked_stores.filter(id=int(store_id)).first()
                print("store", store)
                affected_stores.append(str(store.id))

                store.wallet.put_transaction_on_hold(
                    order=order,
                )

                order.update_store_status(store_id=store.id, status="failed-refund")
                # break the loop when one store has been marked as failed-refund
                break

        store_statuses = []
        # get all order store status
        for status in order.stores_status:
            # replace affected stores status with failed-refund
            if status["storeId"] in affected_stores:
                status["status"] = "failed-refund"
                store_statuses.append(status)
            store_statuses.append(status["status"])

        # check if all the stores has failed-refund to the user
        if all(status == "failed-refund" for status in store_statuses):
            # update the order payment status
            order.order_payment_status = "failed-refund"
            order.save()
            # notify the user
            order.notify_user(
                message="Order {} refund has failed".format(
                    order.get_order_display_id()
                )
            )

        # check if some stores has failed-refund to the user
        if any(status == "failed-refund" for status in store_statuses):
            # update the order payment status
            order.order_payment_status = "partially-failed-refund"
            order.save()
            # notify the user
            order.notify_user(
                message="Order {} refund has partially failed".format(
                    order.get_order_display_id()
                )
            )


def get_paystack_balance(currency="NGN"):
    import requests

    PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY

    url = "https://api.paystack.co/balance"
    headers = {
        "Authorization": "Bearer " + PAYSTACK_SECRET_KEY,
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        response = response.json()
        if response["status"] == True:
            balances = response["data"]
            balance = None
            for balance in balances:
                if balance["currency"] == currency:
                    balance = Decimal(balance["balance"]) / 100
                    break
            return balance


def calculate_delivery_fee(amount, fee, distance=None, price_per_km=None):
    """
    This function is used to calculate the delivery fee
    """

    amount = Decimal(amount)

    delivery_fee = Decimal(fee)

    if amount >= 2500 and not delivery_fee <= 100:
        delivery_fee = amount * Decimal(0.05) + delivery_fee

    if distance and price_per_km:
        delivery_fee = Decimal(distance) * Decimal(price_per_km)

    if delivery_fee <= 100:
        delivery_fee = Decimal(100)

    # round up the delivery fee to the next whole number not decimal
    delivery_fee = delivery_fee.quantize(Decimal("1"), rounding="ROUND_UP")

    return delivery_fee
