from trayapp.base_filters import DateTypeFilter
from django_filters import FilterSet, CharFilter, NumberFilter
from product.models import Item, Order, Rating
from users.models import DeliveryPerson
from django.db.models import Q


class ItemFilter(FilterSet):
    type = CharFilter(field_name="product_menu__type__slug", lookup_expr="exact")

    store_nickname = CharFilter(method="filter_by_store_nickname")
    school = CharFilter(field_name="product_creator__school__slug", lookup_expr="exact")
    country = CharFilter(field_name="product_creator__country", lookup_expr="icontains")
    campus = CharFilter(field_name="product_creator__campus", lookup_expr="exact")
    location = CharFilter(
        field_name="product_creator__store_address", lookup_expr="icontains"
    )
    category = CharFilter(method="filter_by_category")
    store_menu_name = CharFilter(method="filter_by_store_menu_name")
    # store_menu_name = CharFilter(field_name="product_menu__name", lookup_expr="exact")

    class Meta:
        model = Item
        fields = {
            "product_name": ["icontains"],
            "product_slug": ["icontains"],
            "product_price": ["exact", "lt", "gt"],  # lt = less than, gt = greater than
        }

    def filter_by_category(self, queryset, name, value):
        # filter by product_categories
        return queryset.filter(
            id__in=[
                item.id
                for item in queryset
                if item.product_categories.filter(slug=value).exists()
            ]
        )

    def filter_by_store_nickname(self, queryset, name, value):
        return queryset.filter(
            id__in=[
                item.id
                for item in queryset
                if item.product_creator.store_nickname.lower() == value.lower()
            ]
        )
    
    def filter_by_store_menu_name(self, queryset, name, value: str):
        return queryset.filter(
            id__in=[
                item.id
                for item in queryset
                if item.product_menu and item.product_menu.name.lower() == value.lower()
            ]
        )


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
    search_query = CharFilter(method="filter_by_search_query")

    def filter_by_order_status(self, queryset, name, value):
        if value == "READY":
            # filter by ready for pickup or delivery
            return queryset.filter(
                id__in=[
                    order.id
                    for order in queryset
                    if order.get_order_status(self.request.user.profile).upper()
                    == "READY_FOR_PICKUP"
                    or order.get_order_status(self.request.user.profile).upper()
                    == "READY_FOR_DELIVERY"
                    or order.get_order_status(self.request.user.profile).upper()
                    == "NO_DELIVERY_PERSON"
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

    def filter_by_search_query(self, queryset: list[Order], name, value):
        return queryset.filter(
            id__in=[
                order.id
                for order in queryset
                if value.lower() in order.get_display_shipping_address().lower()
                or value.lower() in order.get_order_display_id().lower()
                or value.lower() in order.order_confirm_pin.lower()
            ]
        )

    class Meta:
        model = Order
        fields = {"order_status": ["exact"]}


class DeliveryPersonFilter(DefaultOrderFilter, FilterSet):
    order_status = CharFilter(method="filter_by_order_status")
    search_query = CharFilter(method="filter_by_search_query")


    def filter_by_order_status(self, queryset, name, value):
        value = value.lower()
        delivery_person: DeliveryPerson = self.request.user.profile.get_delivery_person()

        if value == "new":
            # Get all order IDs from delivery person notifications
            order_ids = delivery_person.get_notifications().values_list('order_id', flat=True)

            return Order.objects.filter(id__in=order_ids)

        delivery_person_id = delivery_person.id

        if value == "ongoing":
            # Filter by ready for pickup or delivery
            return queryset.filter(
                Q(delivery_people__contains=[{'id': delivery_person_id, 'status': 'out-for-delivery'}]) |
                Q(delivery_people__contains=[{'id': delivery_person_id, 'status': 'pending'}])
            )

        # General case for other statuses
        return queryset.filter(
            delivery_people__contains=[{'id': delivery_person_id, 'status': value.replace("-", "_")}]
        )

    def filter_by_search_query(self, queryset: list[Order], name, value):
        return queryset.filter(
            id__in=[
                order.id
                for order in queryset
                if value.lower() in order.get_display_shipping_address().lower()
                or value.lower() in order.get_order_display_id().lower()
                or value.lower() in order.order_confirm_pin.lower()
            ]
        )