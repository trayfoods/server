from django_filters import FilterSet, NumberFilter
from users.models import Transaction


class TransactionFilter(FilterSet):
    # add custom filters
    year = NumberFilter(field_name="created_at", lookup_expr="year")  # eg. 2020, 2021
    month = NumberFilter(
        field_name="created_at", lookup_expr="month"
    )  # eg. 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    day = NumberFilter(
        field_name="created_at", lookup_expr="day"
    )  # eg. 1, 2, 3, 4, 5, 6, 7

    class Meta:
        model = Transaction
        fields = {
            "amount": ["exact", "lt", "gt"],
            "desc": ["icontains"],
            "_type": ["exact"],
            "status": ["exact"],
        }
