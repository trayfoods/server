from django_filters import FilterSet, CharFilter, NumberFilter
from product.models import Item, Order


class ItemFilter(FilterSet):
    type = CharFilter(field_name="product_type__slug", lookup_expr="exact")
    # category = CharFilter(
    #     field_name="product_categories__slug", lookup_expr="exact"
    # )

    store_nickname = CharFilter(
        field_name="product_creator__store_nickname", lookup_expr="exact"
    )
    school = CharFilter(
        field_name="product_creator__school__slug", lookup_expr="exact"
    )
    country = CharFilter(
        field_name="product_creator__store_country", lookup_expr="icontains"
    )
    location = CharFilter(
        field_name="product_creator__store_address", lookup_expr="icontains"
    )

    class Meta:
        model = Item
        fields = {
            "product_name": ["icontains"],
            "product_slug": ["icontains"],
            "product_price": ["exact", "lt", "gt"],  # lt = less than, gt = greater than
        }


class OrderFilter(FilterSet):
    from trayapp.base_filters import DateTypeFilter

    year = NumberFilter(field_name="created_at", lookup_expr="year")  # eg. 2020, 2021
    month = NumberFilter(
        field_name="created_at", lookup_expr="month"
    )  # eg. 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    day = NumberFilter(
        field_name="created_at", lookup_expr="day"
    )  # eg. 1, 2, 3, 4, 5, 6, 7

    date_type = DateTypeFilter(field_name="created_at")

    class Meta:
        model = Order
        fields = {"order_status": ["exact"]}
