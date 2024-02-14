from trayapp.base_filters import DateTypeFilter
from django_filters import FilterSet, CharFilter, NumberFilter
from product.models import Item, Order, Rating


class ItemFilter(FilterSet):
    type = CharFilter(field_name="product_type__slug", lookup_expr="exact")

    store_nickname = CharFilter(
        field_name="product_creator__store_nickname", lookup_expr="exact"
    )
    school = CharFilter(field_name="product_creator__school__slug", lookup_expr="exact")
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


class ReviewFilter(FilterSet):
    class Meta:
        model = Rating
        fields = "__all__"


class DefaultOrderFilter(FilterSet):
    year = NumberFilter(field_name="created_at", lookup_expr="year")  # eg. 2020, 2021
    month = NumberFilter(
        field_name="created_at", lookup_expr="month"
    )  # eg. 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    day = NumberFilter(
        field_name="created_at", lookup_expr="day"
    )  # eg. 1, 2, 3, 4, 5, 6, 7

    date_type = DateTypeFilter(field_name="created_at")


class OrderFilter(DefaultOrderFilter, FilterSet):
    class Meta:
        model = Order
        fields = {"order_status": ["exact"]}


class StoreOrderFilter(DefaultOrderFilter, FilterSet):
    order_status = CharFilter(method="filter_by_order_status")

    def filter_by_order_status(self, queryset, name, value):
        if value == "READY":
            # filter by ready for pickup or delivery
            print(queryset)
            return queryset.filter(
                id__in=[
                    order.id
                    for order in queryset
                    if order.get_order_status(self.request.user.profile).upper()
                    == "READY_FOR_PICKUP"
                    or order.get_order_status(self.request.user.profile).upper()
                    == "READY_FOR_DELIVERY"
                ]
            )
        elif value == "COMPLETED":
            # filter by completed
            return queryset.filter(
                id__in=[
                    order.id
                    for order in queryset
                    if order.get_order_status(self.request.user.profile).upper()
                    == "DELIVERED"
                    or order.get_order_status(self.request.user.profile).upper()
                    == "PICKED_UP"
                ]
            )
        return queryset.filter(
            id__in=[
                order.id
                for order in queryset
                if order.get_order_status(self.request.user.profile).upper()
                == value.upper()
            ]
        )

    class Meta:
        model = Order
        fields = {"order_status": ["exact"]}


class DeliveryPersonFilter(DefaultOrderFilter, FilterSet):
    order_status = CharFilter(method="filter_by_order_status")

    def filter_by_order_status(self, queryset, name, value):
        if value == "ongoing":
            # filter by ready for pickup or delivery
            return queryset.filter(
                id__in=[
                    order.id
                    for order in queryset
                    if order.get_delivery_person(
                        delivery_person_id=self.request.user.profile.get_delivery_person().id
                    )["status"].upper()
                    == "OUT-FOR-DELIVERY"
                    or order.get_delivery_person(
                        delivery_person_id=self.request.user.profile.get_delivery_person().id
                    )["status"].upper()
                    == "PICKED-UP"
                ]
            )
        return queryset.filter(
            id__in=[
                order.id
                for order in queryset
                if order.get_delivery_person(
                    delivery_person_id=self.request.user.profile.get_delivery_person().id
                )["status"].upper()
                == value.upper()
            ]
        )
