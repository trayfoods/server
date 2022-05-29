from django.contrib import admin
from product.models import Item, ItemImage, ItemAttribute


class ItemAdmin(admin.ModelAdmin):
    list_display = ("product_name", "product_category",
                    "product_type", "product_price",)
    prepopulated_fields = {"product_slug": (
        "product_name", "product_category", "product_type")}


class ItemAttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "_type",)
    prepopulated_fields = {"urlParamName": ("_type", "name")}


admin.site.register(Item, ItemAdmin)
admin.site.register(ItemAttribute, ItemAttributeAdmin)
admin.site.register(ItemImage)
