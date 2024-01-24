from django.core.management.base import BaseCommand
from product.models import Order


class Command(BaseCommand):
    help = "Mark Orders that has not found any delivery person as `no-delivery-person`"

    def handle(self, *args, **kwargs):
        # Find all unsettled transactions older than 24 hours
        orders = Order.objects.filter(
            status="pending", delivery_person=None
        )

        # Update those transactions to 'settled'
        for order in orders:
            order.status = "no-delivery-person"
            order.save()
            # Add any additional logic here, such as sending notifications

        self.stdout.write(self.style.SUCCESS("Successfully updated orders"))