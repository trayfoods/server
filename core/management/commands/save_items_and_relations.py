import datetime
import json
from django.core.management.base import BaseCommand
from users.models import Vendor, Store, Gender
from product.models import Item, ItemImage, ItemAttribute
from trayapp.permissions import superuser_and_admin_required
from django.core.serializers.json import DjangoJSONEncoder

class Command(BaseCommand):
    help = "Save Items and Ttems Relations data to a JSON file"

    @superuser_and_admin_required(email_subject=help)
    def handle(self, *args, **options):
        items = Item.get_items().all().values()
        item_images = ItemImage.objects.all().values()
        vendors = Vendor.objects.all().values()
        stores = Store.objects.all().values()
        item_attributes = ItemAttribute.objects.all().values()
        genders = Gender.objects.all().values()

        # Convert datetime fields to strings
        items = self.convert_datetime_fields(items)
        item_images = self.convert_datetime_fields(item_images)
        vendors = self.convert_datetime_fields(vendors)
        stores = self.convert_datetime_fields(stores)
        item_attributes = self.convert_datetime_fields(item_attributes)
        genders = self.convert_datetime_fields(genders)

        data = {
            "items": list(items),
            "item_images": list(item_images),
            "vendors": list(vendors),
            "stores": list(stores),
            "item_attributes": list(item_attributes),
            "genders": list(genders),
        }

        json_data = json.dumps(data, indent=4, cls=DjangoJSONEncoder)

        with open("items_and_relations.json", "w") as file:
            file.write(json_data)

        self.stdout.write(
            self.style.SUCCESS("Tables data saved to items_and_relations.json")
        )

    def convert_datetime_fields(self, queryset):
        """
        Convert datetime fields in the queryset to strings.
        """
        datetime_fields = ["created_at", "modified_at", "product_created_on"]  # Add any other datetime fields

        for obj in queryset:
            for field in datetime_fields:
                if field in obj and isinstance(obj[field], datetime.datetime):
                    obj[field] = obj[field].isoformat()

        return queryset
