# Inside your app's management/commands directory, create a file named settle_transactions.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from users.models import Transaction


class Command(BaseCommand):
    help = "Settle transactions that are older than 24 hours"

    def handle(self, *args, **kwargs):
        # Calculate the time for 24 hours ago
        time_threshold = timezone.now() - timedelta(minutes=5)

        # Find all unsettled transactions older than 24 hours
        unsettled_transactions = Transaction.objects.filter(
            status="unsettled", created_at__lte=time_threshold
        )

        # Update those transactions to 'settled'
        for transaction in unsettled_transactions:
            transaction.settle()
            # Add any additional logic here, such as sending notifications

        self.stdout.write(self.style.SUCCESS("Successfully settled transactions"))
