import json
from django.core.management.base import BaseCommand
from trayapp.permissions import superuser_and_admin_required
from users.models import Profile, UserAccount


class Command(BaseCommand):
    help = "Load user and profile data from a JSON file"

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str, help="Path to the JSON file")

    # @superuser_and_admin_required(email_subject=help)
    def handle(self, *args, **options):
        file_path = options["file_path"]

        with open(file_path, "r") as file:
            json_data = json.load(file)

        users_data = json_data.get("users", [])
        profiles_data = json_data.get("profiles", [])

        for user_data in users_data:
            user_data["password"] = user_data["password"]
            user = UserAccount(**user_data)
            user.save()

        for profile_data in profiles_data:
            profile = Profile(**profile_data)
            profile.save()

        self.stdout.write(
            self.style.SUCCESS("User profiles loaded from the JSON file.")
        )
