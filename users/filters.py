from django.utils import timezone
from django_filters import FilterSet, NumberFilter, CharFilter
from users.models import Transaction

DATE_FILTER_TYPES = ["today", "7days", "30days"]


class DateTypeFilter(CharFilter):
    def filter(self, qs, value):
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


class TransactionFilter(FilterSet):
    # add custom filters
    year = NumberFilter(field_name="created_at", lookup_expr="year")  # eg. 2020, 2021
    month = NumberFilter(
        field_name="created_at", lookup_expr="month"
    )  # eg. 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    day = NumberFilter(
        field_name="created_at", lookup_expr="day"
    )  # eg. 1, 2, 3, 4, 5, 6, 7

    date_type = DateTypeFilter(field_name="created_at")

    class Meta:
        model = Transaction
        fields = {
            "amount": ["exact", "lt", "gt"],
            "desc": ["icontains"],
            "_type": ["exact"],
            "status": ["exact"],
        }
