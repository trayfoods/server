import os
from django.conf import settings
from django.contrib import admin
from django.utils.safestring import mark_safe
from product.models import Item, ItemImage, ItemAttribute, Order, Rating


class ItemImageInlineAdmin(admin.TabularInline):
    model = ItemImage

class RatingInlineAdmin(admin.TabularInline):
    model = Rating


class ItemAdmin(admin.ModelAdmin):
    inlines = [ItemImageInlineAdmin, RatingInlineAdmin]
    list_display = ("product_name", "product_category",
                    "product_type", "product_price",)
    prepopulated_fields = {"product_slug": (
        "product_name", "product_category", "product_type")}
    readonly_fields = ("product_images",)


class ItemAttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "_type",)
    prepopulated_fields = {"urlParamName": ("_type", "name")}


# ItemImage
def get_item_original_image(obj):
    src = obj.item_image.url if obj.item_image and \
        hasattr(obj.item_image, 'url') else os.path.join(
            settings.STATIC_URL, 'img/item/default.jpg')
    return mark_safe('<img src="{}" height="500" style="border:1px solid #ccc">'.format(src))


get_item_original_image.short_description = 'Original Image'
get_item_original_image.allow_tags = True


# ItemImage Webp
def get_item_webp_image(obj):
    src = obj.item_image_webp.url if obj.item_image_webp and \
        hasattr(obj.item_image_webp, 'url') else os.path.join(
            settings.STATIC_URL, 'img/item/default.jpg')
    return mark_safe('<img src="{}" height="500" style="border:1px solid #ccc">'.format(src))


get_item_webp_image.short_description = 'Webp Image'
get_item_webp_image.allow_tags = True


class ItemImageAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'item_image')
    search_fields = ['product__product_name', 'item_image', 'product__product_slug']
    fields = (
        'product', 'is_primary',
        get_item_original_image, get_item_webp_image, 'item_image',
    )
    readonly_fields = (get_item_original_image, get_item_webp_image)


admin.site.register(Item, ItemAdmin)
admin.site.register(Rating)
admin.site.register(ItemAttribute, ItemAttributeAdmin)
admin.site.register(ItemImage, ItemImageAdmin)
admin.site.register(Order)
