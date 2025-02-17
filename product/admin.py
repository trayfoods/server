import os
from django.conf import settings
from django.contrib import admin
from django.utils.safestring import mark_safe
from product.models import Item, ItemImage, ItemAttribute, Order, Rating
from users.admin import DeliveryInline


class ItemImageInlineAdmin(admin.TabularInline):
    model = ItemImage


class RatingInlineAdmin(admin.TabularInline):
    model = Rating


class ItemAdmin(admin.ModelAdmin):
    inlines = [ItemImageInlineAdmin, RatingInlineAdmin]
    list_display = (
        "product_name",
        "product_price",
        "product_qty_unit",
        "product_menu",
        "product_status",
    )
    search_fields = (
        "product_name",
        "product_menu__name",
        "product_creator__store_name",
    )
    readonly_fields = (
        "product_images",
        "product_slug",
        "product_price",
        "product_clicks",
        "product_views",
    )
    list_filter = ("product_creator__store_nickname", "product_status")


class ItemInline(admin.TabularInline):
    model = Item
    extra = 0


class ItemAttributeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "_type",
        "parent",
    )
    list_filter = ("_type",)
    prepopulated_fields = {"slug": ("_type", "name")}


# ItemImage
def get_item_original_image(obj):
    src = (
        obj.item_image.url
        if obj.item_image and hasattr(obj.item_image, "url")
        else os.path.join(settings.STATIC_URL, "img/item/default.jpg")
    )
    return mark_safe(
        '<img src="{}" height="500" style="border:1px solid #ccc">'.format(src)
    )


get_item_original_image.short_description = "Original Image"
get_item_original_image.allow_tags = True


class ItemImageAdmin(admin.ModelAdmin):
    list_display = ("__str__", "item_image", "is_primary")
    search_fields = ["product__product_name", "item_image", "product__product_slug"]
    fields = (
        "product",
        "is_primary",
        get_item_original_image,
        "item_image",
    )
    readonly_fields = ("item_image", get_item_original_image)


class RatingAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "stars",
        "updated_at",
    )
    # readonly_fields = ("users_liked", "stars")
    search_fields = ["user__username", "item__product_name"]


class OrderAdmin(admin.ModelAdmin):
    inlines = [DeliveryInline]
    list_display = (
        "__str__",
        "order_status",
        "overall_price",
        "created_at",
        "order_payment_status",
    )
    readonly_fields = (
        "order_track_id",
        "overall_price",
        "order_gateway_fee",
        "order_confirm_pin",
        "delivery_fee_percentage",
        "service_fee",
        "delivery_fee",
        "order_payment_url",
        "prev_order_track_id",
        "activities_log",
        "profiles_seen",
    )
    search_fields = [
        "user__username",
        "order_track_id",
        "prev_order_track_id",
        "order_status",
        "stores_infos",
        "stores_status",
    ]


admin.site.register(Item, ItemAdmin)
admin.site.register(Rating, RatingAdmin)
admin.site.register(ItemAttribute, ItemAttributeAdmin)
admin.site.register(ItemImage, ItemImageAdmin)
admin.site.register(Order, OrderAdmin)
