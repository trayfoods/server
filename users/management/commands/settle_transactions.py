from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from users.models import Transaction, Wallet
import logging


class Command(BaseCommand):
    help = "Settle transactions that are older than 24 hours"
    logging.info("Settle transactions that are older than 24 hours")

    def handle(self, *args, **kwargs):
        # Calculate the time for 24 hours ago
        time_threshold = timezone.now() - timedelta(hours=24)

        # Find all unsettled transactions older than 24 hours
        unsettled_transactions = Transaction.objects.filter(
            status="unsettled", 
            # created_at__lte=time_threshold
        )

        # Update those transactions to 'settled'
        transactions_grouped_by_wallet = (
            []
        )  # {"wallet": transaction.wallet.id, "amount": transaction.amount}
        for transaction in unsettled_transactions:
            transaction.settle()
            # add the wallet if it doesn't exist in the list
            # then keep adding the amount to the wallet in the list
            # no duplicate wallet in the list
            wallet: Wallet = transaction.wallet
            amount = transaction.amount
            if not any(
                transaction["wallet"] == wallet
                for transaction in transactions_grouped_by_wallet
            ):
                transactions_grouped_by_wallet.append(
                    {"wallet": wallet, "amount": amount}
                )
            else:
                for transaction in transactions_grouped_by_wallet:
                    if transaction["wallet"] == wallet:
                        transaction["amount"] += amount

        # notify the user of the transactions settled
        for transaction in transactions_grouped_by_wallet:
            wallet: Wallet = transaction["wallet"]
            wallet.send_wallet_alert(transaction["amount"])

        self.stdout.write(self.style.SUCCESS("Successfully settled transactions"))
