import datetime
import json
from django.core.management.base import BaseCommand
from trayapp.permissions import superuser_and_admin_required
from users.models import (
    Profile,
    UserAccount,
) 
from django.core.serializers.json import DjangoJSONEncoder


class Command(BaseCommand):
    help = "Save user and profile data to a JSON file"

    @superuser_and_admin_required(email_subject=help)
    def handle(self, *args, **options):
        users = UserAccount.objects.all().values()
        profiles = Profile.objects.all().values()

        # Convert datetime fields to strings
        users = self.convert_datetime_fields(users)
        profiles = self.convert_datetime_fields(profiles)

        data = {"users": list(users), "profiles": list(profiles)}

        json_data = json.dumps(data, indent=4, cls=DjangoJSONEncoder)

        with open("user_profiles.json", "w") as file:
            file.write(json_data)

        self.stdout.write(
            self.style.SUCCESS("User profiles saved to user_profiles.json")
        )

    def convert_datetime_fields(self, queryset):
        """
        Convert datetime fields in the queryset to strings.
        """
        datetime_fields = ["created_at", "modified_at"]  # Add any other datetime fields

        for obj in queryset:
            for field in datetime_fields:
                if field in obj and isinstance(obj[field], datetime.datetime):
                    obj[field] = obj[field].isoformat()

        return queryset
