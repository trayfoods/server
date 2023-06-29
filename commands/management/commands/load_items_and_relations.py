import json
from django.core.management.base import BaseCommand
from users.models import Vendor, Store, Gender
from product.models import Item, ItemImage, ItemAttribute
from trayapp.permissions import superuser_and_admin_required


class Command(BaseCommand):
    help = 'Load Items and Ttems Relations data from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the JSON file')

    @superuser_and_admin_required(email_subject=help)
    def handle(self, *args, **options):
        file_path = options['file_path']

        # Load data from JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)

        # Clear existing data from tables
        Item.objects.all().delete()
        ItemImage.objects.all().delete()
        Vendor.objects.all().delete()
        Store.objects.all().delete()
        ItemAttribute.objects.all().delete()
        Gender.objects.all().delete()

        # Bulk create objects
        Item.objects.bulk_create([Item(**item) for item in data['items']])
        ItemImage.objects.bulk_create([ItemImage(**image) for image in data['item_images']])
        Vendor.objects.bulk_create([Vendor(**vendor) for vendor in data['vendors']])
        Store.objects.bulk_create([Store(**store) for store in data['stores']])
        ItemAttribute.objects.bulk_create([ItemAttribute(**attribute) for attribute in data['item_attributes']])
        Gender.objects.bulk_create([Gender(**gender) for gender in data['genders']])

        self.stdout.write(self.style.SUCCESS('Tables data loaded from JSON file'))
