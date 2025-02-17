import logging

from django.http import HttpResponse
from product.models import Order
from users.models import Store, Transaction, Profile, Wallet
from trayapp.decorators import get_time_complexity
from decimal import Decimal

from django.conf import settings
from django.db.models import Q


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
        logging.info("event_type", self.event_type)
        if self.event_type == "charge.dispute.create":
            return self.charge_dispute_create()
        if self.event_type == "charge.dispute.remind":
            return self.charge_dispute_remind()
        if self.event_type == "charge.dispute.resolve":
            return self.charge_dispute_resolve()
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

    def charge_dispute_create(self):
        # send an email to support@trayfoods.com about the dispute with it's data
        from django.core.mail import EmailMessage

        email = EmailMessage(
            "Charge Dispute",
            f"Charge Dispute\n\n{self.event_data}",
            settings.EMAIL_HOST_USER,
            ["support@trayfoods.com"],
        )
        email.send()

        return HttpResponse("Charge Dispute", status=200)

    def charge_dispute_remind(self):
        # send an email to support@trayfoods.com about the dispute with it's data
        from django.core.mail import EmailMessage

        email = EmailMessage(
            "Charge Dispute Remind",
            f"Charge Dispute Remind\n\n{self.event_data}",
            settings.EMAIL_HOST_USER,
            ["support@trayfoods.com"],
        )
        email.send()
        return HttpResponse("Charge Dispute Remind", status=200)

    def charge_dispute_resolve(self):
        # send an email to support@trayfoods.com about the dispute with it's data
        from django.core.mail import EmailMessage

        email = EmailMessage(
            "Charge Dispute Resolve",
            f"Charge Dispute Resolve\n\n{self.event_data}",
            settings.EMAIL_HOST_USER,
            ["support@trayfoods.com"],
        )
        email.send()
        return HttpResponse("Charge Dispute Resolve", status=200)

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

        def caluate_gateway_fee(order_price):
            gateway_fee = 0
            if order_price <= 2500:
                gateway_fee = 100
            elif order_price > 2500:
                gateway_fee = order_price * Decimal(0.025) + 100
            return gateway_fee

        order_gateway_fee = caluate_gateway_fee(order_price)

        # get the order from the database
        order_qs = (
            Order.objects.select_related("user")
            .filter(Q(order_track_id=order_id) | Q(prev_order_track_id=order_id))
            .exclude(order_payment_status="success")
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
            order.order_payment_status = "awaiting-refund-action"
            order.order_status = "failed"
            order.save()
            order.notify_user(
                title="Payment Failed",
                message="Payment for Order {} has failed, kindly contact support for your refund".format(
                    order.get_order_display_id()
                ),
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

            shipping_address = order.shipping
            shipping_address = shipping_address.get("address", None)

            order_user: Profile = order.user

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
                            store.update_product_qty(
                                product_slug, product_cart_qty, "remove"
                            )

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

                    order.notify_store(
                        store_id=store.id,
                        title="New Order",
                        message="New Order of {} {} was made by {}, tap on this link to view your new orders {}/account/?tab=store-orders".format(
                            order.order_currency,
                            overrall_store_price,
                            order_user.user.username,
                            settings.FRONTEND_URL,
                        ),
                    )

            if order.user:
                # notify the user
                order.notify_user(
                    title="Order Placed",
                    message="Your Order {} has been placed, we will notify you when it has been accepted".format(
                        order.get_order_display_id()
                    ),
                )

            order.save()

        return HttpResponse("Payment successful", status=200)

    def transfer_success(self):
        amount = self.event_data["amount"]
        transaction_id = self.event_data["reference"]
        gateway_transfer_id = self.event_data["id"]
        transfer_status = self.event_data["status"]

        # get transaction from the database
        transaction = (
            Transaction.objects.select_related("wallet")
            .filter(transaction_id=transaction_id)
            .first()
        )

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

        # check if the transaction is not pending
        if transaction.status != "pending":
            return HttpResponse("Transfer already processed", status=200)

        if "success" == transfer_status:
            account_name = self.event_data["recipient"]["name"]
            # deduct the amount_with_charges from the wallet
            wallet: Wallet = transaction.wallet
            kwargs = {
                "amount": amount,
                "transaction_id": transaction_id,
                "transfer_fee": transaction.transfer_fee,
                "desc": f"We have successfully transferred {amount} {wallet.currency} to {account_name}",
                "status": "success",
            }
            wallet.deduct_balance(**kwargs)

            # update the transaction status
            transaction.status = "success"
            transaction.gateway_transfer_id = gateway_transfer_id
            transaction.desc = "We have successfully transferred {} {} to {}".format(
                transaction.amount, wallet.currency, account_name
            )
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
        transaction = (
            Transaction.objects.select_related("wallet")
            .filter(transaction_id=transaction_id)
            .first()
        )

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

            profile: Profile = transaction.wallet.profile

            # notify the user
            profile.notify_me(
                title="Transfer Failed",
                message="Transfer of {} {} has failed".format(
                    transaction.amount, transaction.wallet.currency
                ),
            )
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
        transaction = (
            Transaction.objects.select_related("wallet")
            .filter(transaction_id=transaction_id)
            .first()
        )

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
                "desc": "We have reversed the transfer to " + account_name,
            }
            transaction.wallet.reverse_transaction(**kwargs)
            # update the transaction status
            transaction.status = "reversed"
            transaction.gateway_transfer_id = gateway_transfer_id
            transaction.save()
            return HttpResponse("Transfer Reversed", status=200)

        return HttpResponse("Transfer Process Failed", status=400)

    def refund_processed(self):
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
            Q(order_track_id=order_id) | Q(prev_order_track_id=order_id)
        )

        if not order_qs.exists():
            return HttpResponse("Order does not exist", status=404)

        # get the order from the database
        order = order_qs.first()

        # deduct the amount from all stores that are involved in the order
        stores_infos = order.stores_infos
        refund_store_id = None
        refund_store_name = None
        for store_info in stores_infos:
            store_id = store_info.get("storeId")
            if not store_id:
                continue

            store_status = order.get_store_status(store_id)
            total = store_info["total"]
            # get the store total normal price
            store_total_price = total.get("price", 0)
            # get the store plate price
            store_plate_price = total.get("plate_price", 0)
            # get the store option groups price
            store_option_groups_price = total.get("option_groups_price", 0)

            # get store delivery fee by dividing the delivery fee by the number of stores
            store_delivery_fee = (
                order.delivery_fee + Decimal(order.delivery_fee_percentage)
            ) / len(stores_infos)

            overrall_store_price = (
                Decimal(store_total_price)
                + Decimal(store_plate_price)
                + Decimal(store_option_groups_price)
                + Decimal(store_delivery_fee)
            )

            # if it's only one store that is involved in the order add service fee and delivery fee
            if len(stores_infos) == 1:
                overrall_store_price += Decimal(order.service_fee)

            if store_status == "pending-refund" and overrall_store_price == order_price:
                store: Store = order.linked_stores.filter(id=int(store_id)).first()
                # check if the store status is "pending-refund"
                if store:
                    order_transaction = (
                        store.wallet.get_transactions().filter(order=order).first()
                    )
                    if order_transaction:
                        store.wallet.deduct_balance(
                            amount=Decimal(store_total_price)
                            + Decimal(store_plate_price)
                            + Decimal(store_option_groups_price),
                            _type="refund",
                            desc="Refund for Order {}".format(
                                order.get_order_display_id()
                            ),
                            order=order,
                        )

                    order.update_store_status(store_id=store.id, status="refunded")
                    order.funds_refunded += order_price
                    order.save()
                    refund_store_id = store.id
                    refund_store_name = store.store_name
                break  # break the loop when one store has been refunded

        if refund_store_id is None:
            return HttpResponse("No Store Has Pending Refund", status=400)

        store_statuses = order.stores_status
        store_statuses = [status.get("status", None) for status in store_statuses]

        # check if all the stores has refunded to the user
        if all(status == "refunded" for status in store_statuses):
            # update the order payment status
            order.order_payment_status = "refunded"
            order.save()
        # check if some stores has refunded to the user
        elif any(status == "refunded" for status in store_statuses):
            # update the order payment status
            order.order_payment_status = "partially-refunded"
            order.save()

        # notify the user
        order.notify_user(
            title="Refund from {}".format(refund_store_name),
            message="Your Order {} has been refunded by {}".format(
                order.get_order_display_id(),
                refund_store_name,
            ),
        )

        order.log_activity(
            title="Refund from {}".format(refund_store_name),
            description="Order {} has been refunded by {}".format(
                order.get_order_display_id(), refund_store_name
            ),
            activity_type="refund",
        )

        return HttpResponse("Refund successful", status=200)

    def refund_failed(self):
        """
        Refund has failed to process.
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
            Q(order_track_id=order_id) | Q(prev_order_track_id=order_id)
        )

        if not order_qs.exists():
            return HttpResponse("Order does not exist", status=404)

        # get the order from the database
        order = order_qs.first()

        # deduct the amount from all stores that are involved in the order
        stores_infos = order.stores_infos
        refund_store_id = None
        refund_store_name = None
        for store_info in stores_infos:
            store_id = store_info.get("storeId")
            if not store_id:
                continue

            store_status = order.get_store_status(store_id)
            total = store_info["total"]
            # get the store total normal price
            store_total_price = total.get("price", 0)
            # get the store plate price
            store_plate_price = total.get("plate_price", 0)
            # get the store option groups price
            store_option_groups_price = total.get("option_groups_price", 0)

            # get store delivery fee by dividing the delivery fee by the number of stores
            store_delivery_fee = order.delivery_fee / len(stores_infos)

            overrall_store_price = (
                Decimal(store_total_price)
                + Decimal(store_plate_price)
                + Decimal(store_option_groups_price)
                + Decimal(store_delivery_fee)
            )
            if store_status == "pending-refund" and overrall_store_price == order_price:
                store: Store = order.linked_stores.filter(id=int(store_id)).first()
                # check if the store status is "pending-refund"
                if store:
                    order_transaction = (
                        store.wallet.get_transactions().filter(order=order).first()
                    )
                    if order_transaction:
                        store.wallet.put_transaction_on_hold(
                            order=order,
                        )

                    order.update_store_status(store_id=store.id, status="failed-refund")
                    refund_store_id = store.id
                    refund_store_name = store.store_name
                break

        if refund_store_id is None:
            return HttpResponse("No Store Has Pending Refund", status=400)

        store_statuses = order.stores_status
        store_statuses = [status.get("status", None) for status in store_statuses]

        # check if all the stores has failed-refund to the user
        if all(status == "failed-refund" for status in store_statuses):
            # update the order payment status
            order.order_payment_status = "failed-refund"
            order.save()
        # check if some stores has failed-refund to the user
        elif any(status == "failed-refund" for status in store_statuses):
            # update the order payment status
            order.order_payment_status = "partially-failed-refund"
            order.save()

        # notify the user
        order.notify_user(
            title="Refund from {}".format(refund_store_name),
            message="Refund for Order {} has failed, kindly contact support".format(
                order.get_order_display_id(),
            ),
        )

        order.log_activity(
            title="Refund from {}".format(refund_store_name),
            description="Refund for Order {} has failed, kindly contact support".format(
                order.get_order_display_id(),
            ),
            activity_type="refund",
        )

        return HttpResponse("Refund Failed Recorded", status=200)


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
