from django.core.management.base import BaseCommand
from product.models import Order


class Command(BaseCommand):
    help = "Mark Orders that has not found any delivery person as `no-delivery-person`"

    def handle(self, *args, **kwargs):
        pass