from django.core.management.base import BaseCommand
from users.models import DeliveryPerson


class Command(BaseCommand):
    help = "Credit all Delivery Person their uncleared balance"

    def handle(self, *args, **kwargs):
        delivery_people = DeliveryPerson.objects.all()
        for delivery_person in delivery_people:
            # credit the delivery person's wallet with the uncleared balance
            kwargs = {
                "amount": delivery_person.wallet.uncleared_balance,
                "title": "Monthly Payout",
                "description": "Monthly payout of uncleared balance",
            }
            delivery_person.wallet.add_balance(**kwargs)
            # clear the delivery person's wallet
            delivery_person.wallet.clear_uncleared_balance()
        self.stdout.write(self.style.SUCCESS("Successfully credited all delivery people their uncleared balance"))
