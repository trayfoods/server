from django_filters import FilterSet, CharFilter
from product.models import Item, Order

class ItemFilter(FilterSet):
    type = CharFilter(field_name="product_type__urlParamName", lookup_expr="exact")
    category = CharFilter(field_name="product_category__urlParamName", lookup_expr="exact")
    
    store_nickname = CharFilter(field_name="product_avaliable_in__store_nickname", lookup_expr="exact")
    school = CharFilter(field_name="product_avaliable_in__store_school__slug", lookup_expr="exact")
    country = CharFilter(field_name="product_avaliable_in__store_country", lookup_expr="icontains")
    location = CharFilter(field_name="product_avaliable_in__store_address", lookup_expr="icontains")

    class Meta:
        model = Item
        fields = {
            "product_name": ["icontains"],
            "product_slug": ["icontains"],
            "product_price": ["exact", "lt", "gt"], # lt = less than, gt = greater than
        }


class OrderFilter(FilterSet):
    class Meta:
        model = Order
        field = {
            "order_status":["exact"]
        }