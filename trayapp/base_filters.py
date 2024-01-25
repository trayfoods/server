from django.utils import timezone
from django_filters import CharFilter

DATE_FILTER_TYPES = ["Alldays", "today", "7days", "30days"]


class DateTypeFilter(CharFilter):
    def filter(self, qs, value):
        # check if the value is null or empty
        if not value:
            return qs
        # check if the value is not in the list of filter types
        if value not in DATE_FILTER_TYPES:
            raise ValueError("Invalid Date Type")

        if value in DATE_FILTER_TYPES:
            if value == "today":
                return qs.filter(created_at__date=timezone.now())
            elif value == "7days":
                return qs.filter(
                    created_at__date__gte=timezone.now().date()
                    - timezone.timedelta(days=7)
                )
            elif value == "30days":
                return qs.filter(
                    created_at__date__gte=timezone.now().date()
                    - timezone.timedelta(days=30)
                )
        return qs
