from django_filters import FilterSet, NumberFilter
from users.models import Transaction


class TransactionFilter(FilterSet):
    # add custom filters
    year = NumberFilter(field_name="created_at", lookup_expr="year")
    month = NumberFilter(field_name="created_at", lookup_expr="month")
    week = NumberFilter(field_name="created_at", lookup_expr="week")

    class Meta:
        model = Transaction
        fields = {
            "title": ["icontains"],
            "amount": ["exact", "lt", "gt"],
            "desc": ["icontains"],
            "_type": ["exact"],
        }
