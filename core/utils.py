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

        order_price = order_price - delivery_fee - Decimal(order.service_fee)

        if overall_price > order_price:
            order.order_payment_status = "refunded"
            order.order_status = "failed"
            order.save()
            return HttpResponse("Payment failed, Processing Refund", status=400)

        if "success" in order_payment_status:
            # get 25% of the delivery fee
            delivery_fee_percentage = delivery_fee * Decimal(0.25)
            new_delivery_fee = delivery_fee - delivery_fee_percentage
            # update the order payment status
            order.order_payment_status = order_payment_status
            order.order_payment_method = order_payment_method
            order.delivery_fee = new_delivery_fee
            order.order_status = "processing"
            order.save()

            shipping_address = order.shipping
            shipping_address = shipping_address.get("address", None)

            if shipping_address == "pickup":
                # send notification to the store
                # order.user.send_push_notification(
                #     "Updates on your order",
                #     f"Order #{order.order_track_id.upper()} has been sent to the store, we will notify you when the store accept the order",
                # )
                # send sms to the user
                order.user.send_sms(
                    f"Order #{order.order_track_id.upper()} has been sent to the store, we will notify you when the store accept the order"
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

        if "success" in transfer_status:
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

        if "failed" in transfer_status:
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

        if "reversed" in transfer_status:
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
