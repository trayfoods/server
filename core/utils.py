import json

from django.http import HttpResponse
from product.models import Order
from users.models import Store, Transaction


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
        # get the order_id from event_data
        order_id = self.event_data["reference"]
        order_payment_status = self.event_data["status"]
        order_payment_method = self.event_data["authorization"]["channel"]
        order_price = self.event_data["amount"]
        order_price = float(order_price) / 100

        # get the order from the database
        order = Order.objects.get(order_track_id=order_id)
        # check if the order is already successful
        if order.order_payment_status == "success":
            return HttpResponse("Payment already successful", status=200)
        order.order_payment_method = order_payment_method

        # get all the needed data to verify the payment
        stores = order.stores_infos
        stores = json.loads(stores)

        delivery_price = float(order.delivery_price)

        # minus delivery_price from overall_price and order_price
        overall_price = float(order.overall_price) - delivery_price
        order_price = order_price - delivery_price

        # minus transaction_fee (10) from overall_price and order_price
        order_price = order_price - 10
        overall_price = overall_price - 10

        # calculate the total price of the stores
        # and compare it with the overall price
        stores_total_price = 0
        stores__ids__with_credits = []
        for store in stores:
            store_id = store["storeId"]
            price = store["total"]["price"]
            plate_price = store["total"]["platePrice"]
            total_price = price + plate_price
            stores__ids__with_credits.append({"id": store_id, "credit": total_price})
            stores_total_price += total_price

        # if the stores_total_price is greater than the overall_price or
        # if the order_price is not equal to the overall_price
        # then the order is not valid
        if stores_total_price > overall_price or order_price != overall_price:
            order.order_payment_status = "failed"
            order.order_status = "cancelled"
            order.order_message = (
                "This Order Was Not Valid, Please Contact The Support Team"
            )
            order.save()
            return HttpResponse("Payment failed, Processing Refund", status=400)

        if "success" in order_payment_status:
            stores_with_issues = []
            # update the balance of the stores
            for store in stores__ids__with_credits:
                store_nickname = store["id"]
                # get the store from the database
                # and update its credit
                store_qs = Store.objects.filter(
                    store_nickname=store_nickname.strip()
                ).first()
                if store_qs:
                    kwargs = {
                        "amount": float(store["credit"]),
                        "description": f"Order Payment From {order.user.username} with order id {order.order_track_id} was successful",
                        "unclear": False,
                        "order": order,
                    }
                    store_qs.credit_wallet(**kwargs)
                    store_qs.save()
                else:
                    stores_with_issues.append(store_id)
            print("stores_with_issues: ", stores_with_issues)
            # update the order payment status
            order.order_payment_status = order_payment_status
            order.order_payment_method = order_payment_method
            order.delivery_price = delivery_price
            order.order_status = "processing"
            order.order_message = "Your Order Payment Was Successful"
            order.save()

            # # send the order to the store
            # order.send_order_to(who="store")

            # # send the order to the user
            # order.send_order_to(who="user")

            # # send the order to the delivery guy
            # order.send_order_to(who="delivery_personnel")

        return HttpResponse("Payment successful", status=200)
        # except Order.DoesNotExist:
        #     return HttpResponse("Order does not exist", status=404)

    def transfer_success(self):
        amount = self.event_data["amount"]
        amount = float(amount) / 100
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

        if transaction.amount != amount:
            return HttpResponse("Invalid amount", status=400)

        # check if the transaction is already successful
        if transaction.status == "success":
            return HttpResponse("Transfer already successful", status=200)

        # check if the transaction is already failed
        if transaction.status == "failed":
            return HttpResponse("Transfer already failed", status=400)

        if "success" in transfer_status:
            account_name = self.event_data["recipient"]["name"]
            # deduct the amount_with_charges from the wallet
            kwargs = {
                "amount": amount,
                "transaction_id": transaction_id,
                "desc": "TRF to " + account_name,
                "status": "success",
                "nor_debit_wallet": True,
            }
            transaction = transaction.wallet.deduct_balance(**kwargs)

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
        amount = float(amount) / 100
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
        amount = float(amount) / 100
        transaction_id = self.event_data["reference"]
        gateway_transfer_id = self.event_data["id"]
        transfer_status = self.event_data["status"]
        failures = self.event_data["failures"]
        account_name = self.event_data["recipient"]["name"]

        if failures:
            return HttpResponse("Transfer failed", status=400)

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
