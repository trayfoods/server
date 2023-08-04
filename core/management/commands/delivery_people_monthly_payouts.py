from django.core.management.base import BaseCommand
from users.models import DeliveryPerson


class Command(BaseCommand):
    help = "Move All Delivery Person cleared balance to their main balance and clear their cleared balance"

    def handle(self, *args, **kwargs):
        delivery_people = DeliveryPerson.objects.all()
        for delivery_person in delivery_people:
            # credit the delivery person's wallet with the cleared balance
            kwargs = {
                "amount": delivery_person.wallet.cleared_balance,
                "title": "Monthly Payout",
                "description": "Monthly payout of cleared balance",
            }
            delivery_person.wallet.add_balance(**kwargs)
            # clear the delivery person's wallet
            delivery_person.wallet.clear_balance(type="cleared")
        self.stdout.write(self.style.SUCCESS("Successfully credited all delivery people their uncleared balance"))
