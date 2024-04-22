from django_filters import FilterSet, NumberFilter, CharFilter
from users.models import Transaction, Store
from django.db.models import Q


class TransactionFilter(FilterSet):
    from trayapp.base_filters import DateTypeFilter

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


class StoreFilter(FilterSet):
    store_category = CharFilter(field_name="store_categories", lookup_expr="icontains")
    school = CharFilter(field_name="school__slug", lookup_expr="exact")
    state = CharFilter(field_name="vendor__state__slug", lookup_expr="exact")
    search_name = CharFilter(method="filter_by_name_nickname")
    gender_preference = CharFilter(method="filter_by_gender_preference")

    class Meta:
        model = Store
        fields = {
            "store_name": ["icontains"],
            "store_nickname": ["icontains"],
            "store_type": ["exact"],
            "country": ["exact"],
            "state": ["exact"],
            "campus": ["exact"],
        }

    def filter_by_gender_preference(self, queryset, name, value):
        # filter stores with gender_preference and still add the ones that does not have the gender preference set
        return queryset.filter(gender_preference__name=value.upper()) | queryset.filter(
            gender_preference__isnull=True
        )

    def filter_by_name_nickname(self, queryset, name, value):
        return queryset.filter(
            Q(store_name__icontains=value) | Q(store_nickname__icontains=value)
        )
