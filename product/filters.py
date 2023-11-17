from django_filters import FilterSet, CharFilter
from product.models import Item

class ItemFilter(FilterSet):
    store_nickname = CharFilter(field_name="product_avaliable_in__store_nickname", lookup_expr="exact")
    school = CharFilter(field_name="product_avaliable_in__store_school__slug", lookup_expr="exact")
    country = CharFilter(field_name="product_avaliable_in__store_country", lookup_expr="icontains")
    location = CharFilter(field_name="product_avaliable_in__store_address", lookup_expr="icontains")

    class Meta:
        model = Item
        fields = {
            "product_name": ["icontains"],
            "product_slug": ["icontains"],
            "product_desc": ["icontains"],
            "product_price": ["exact", "lt", "gt"], # lt = less than, gt = greater than
            "product_category": ["exact"],
            "product_type": ["exact"],
        }