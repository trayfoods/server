import graphene
from graphene_django.types import DjangoObjectType
from graphql import GraphQLError
from .models import Item, ItemAttribute, ItemImage, Order
from users.models import Vendor
from users.types import StoreType

from trayapp.custom_model import JSONField


class ItemImageType(DjangoObjectType):
    product_image = graphene.String()
    product_image_webp = graphene.String()

    class Meta:
        model = ItemImage
        fields = ["id", "product_image", "product_image_webp", "is_primary"]

    def resolve_product_image(self, info, *args, **kwargs):
        product_image = info.context.build_absolute_uri(self.item_image.url)
        return product_image

    def resolve_product_image_webp(self, info, *args, **kwargs):
        product_image_webp = info.context.build_absolute_uri(self.item_image_webp.url)
        return product_image_webp


class ItemAttributeType(DjangoObjectType):
    class Meta:
        model = ItemAttribute
        fields = "__all__"


class ItemType(DjangoObjectType):
    id = graphene.Int(storeNickname=graphene.String(required=False))
    product_images = graphene.List(ItemImageType, count=graphene.Int(required=False))
    is_avaliable = graphene.Boolean()
    has_qty = graphene.Boolean()
    is_avaliable_for_store = graphene.String()
    avaliable_store = graphene.Field(
        StoreType, storeNickname=graphene.String(required=False)
    )

    class Meta:
        model = Item
        fields = [
            "product_name",
            "id",
            "avaliable_store",
            "is_avaliable_for_store",
            "product_clicks",
            "product_views",
            "product_qty",
            "product_slug",
            "product_calories",
            "product_type",
            "product_category",
            "product_images",
            "product_desc",
            "product_price",
            "product_avaliable_in",
            "has_qty",
            "product_creator",
            "product_created_on",
            "is_avaliable",
        ]

    # This will add a unqiue id, if the store items are the same
    def resolve_id(self, info, storeNickname=None):
        item_id = self.id
        if storeNickname:
            storeName = self.product_avaliable_in.filter(
                store_nickname=storeNickname
            ).first()
            if not storeName is None:
                item_id = self.id + storeName.id + Item.objects.last().id
        return item_id

    def resolve_product_qty(self, info):
        product_qty = self.product_qty
        if product_qty == 0:
            product_qty = 1
        return product_qty

    def resolve_has_qty(self, info):
        has_qty = False
        if self.product_qty > 0:
            has_qty = True
        return has_qty

    def resolve_is_avaliable_for_store(self, info):
        user = info.context.user
        store_item = "not_login"
        if user.is_authenticated:
            store_item = "not_vendor"
            vendor = Vendor.objects.filter(user=user.profile).first()
            if not vendor is None:
                is_product_in_store = vendor.store.store_products.filter(
                    product_slug=self.product_slug
                ).first()
                if not is_product_in_store is None:
                    store_item = "1"
                else:
                    store_item = "0"
        return store_item

    def resolve_product_images(self, info, count=None):
        images = ItemImage.objects.filter(product=self)
        if self.product_images.count() == images.count():
            images = images
        else:
            images = self.product_images.all()

        if not count == None:
            count = count + 1
            if images.count() >= count:
                images = images[:count]
                if images is None:
                    images = self.product_images.all()

        return images

    def resolve_is_avaliable(self, info):
        if len(self.product_avaliable_in.all()) > 0:
            is_avaliable = True
        else:
            is_avaliable = False
        return is_avaliable

    def resolve_avaliable_store(self, info, storeNickname=None):
        store = None
        if storeNickname:
            store = self.product_avaliable_in.filter(
                store_nickname=storeNickname
            ).first()
        if store is None:
            is_avaliable = self.product_avaliable_in.count() > 0
            if self.product_creator is None:
                if is_avaliable:
                    store = self.product_avaliable_in.first()
            else:
                isStore = False
                store_qs = self.product_avaliable_in.filter(
                    store_nickname=self.product_creator.store
                ).first()
                if not store_qs is None:
                    isStore = True
                if isStore == True:
                    store = self.product_creator.store
                else:
                    if is_avaliable:
                        store = self.product_avaliable_in.first()
        return store


class TotalOrderType(graphene.InputObjectType):
    price = graphene.Int()
    plate_price = graphene.Int()


class CountOrderType(graphene.InputObjectType):
    items = graphene.Int()
    plate = graphene.Int()


class StoreOrderInfoType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    storeId = graphene.String(required=True)
    total = TotalOrderType(required=True)
    count = CountOrderType(required=True)
    items = graphene.List(JSONField, required=True)


class OrderDetailsType(graphene.InputObjectType):
    overall_price = graphene.Int(required=True)
    stores_infos = graphene.List(StoreOrderInfoType, required=True)


class OrderType(DjangoObjectType):
    id = graphene.ID()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_id",
            "order_user",
            "order_details",
            "order_payment_id",
            "order_payment_currency",
            "order_payment_method",
            "order_payment_status",
            "order_created_on",
        ]

    def resolve_id(self):
        return self.order_id

    def resolve_order_details(self, info, **kwargs):
        order_details = kwargs.pop("order_details", None)
        if order_details is not None:
            try:
                order_details["stores_infos"] = [
                    StoreOrderInfoType(**store_info)
                    for store_info in order_details.get("stores_infos", [])
                ]
            except Exception as e:
                raise GraphQLError(f"Invalid 'order_details': {str(e)}")

        return OrderDetailsType(**order_details)
