import json

import graphene
from graphene_django.types import DjangoObjectType
from graphql import GraphQLError
from .models import Item, ItemAttribute, ItemImage, Order, Rating
from users.models import Vendor, Store
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


class RatingEnum(graphene.Enum):
    ONE_STAR = 1
    TWO_STARS = 2
    THREE_STARS = 3
    FOUR_STARS = 4
    FIVE_STARS = 5


class RatingInputType(graphene.InputObjectType):
    stars = graphene.Field(RatingEnum, required=True)
    comment = graphene.String()


class ReviewsType(DjangoObjectType):
    did_user_like = graphene.Boolean()
    helpful_count = graphene.Int()

    class Meta:
        model = Rating
        fields = "__all__"

    def resolve_did_user_like(self, info, *args, **kwargs):
        user = info.context.user
        if user.is_authenticated:
            return self.users_liked.filter(id=user.id).exists()
        return False

    def resolve_helpful_count(self, info, *args, **kwargs):
        return self.users_liked.count()


class ItemType(DjangoObjectType):
    product_images = graphene.List(ItemImageType, count=graphene.Int(required=False))
    is_avaliable = graphene.Boolean()
    has_qty = graphene.Boolean()
    editable = graphene.Boolean()
    average_rating = graphene.Float()
    reviews = graphene.List(ReviewsType)
    reviews_count = graphene.Int()
    current_user_review = graphene.Field(ReviewsType)
    is_avaliable_for_store = graphene.String()
    avaliable_store = graphene.Field(
        StoreType, store_nickname=graphene.String(required=False)
    )

    class Meta:
        model = Item
        fields = [
            "id",
            "product_name",
            "avaliable_store",
            "is_avaliable_for_store",
            "product_clicks",
            "product_views",
            "product_qty",
            "product_slug",
            "product_calories",
            "product_qty_unit",
            "is_groupable",
            "product_share_visibility",
            "product_category",
            "product_type",
            "product_images",
            "product_desc",
            "product_price",
            "product_avaliable_in",
            "has_qty",
            "editable",
            "average_rating",
            "reviews",
            "reviews_count",
            "current_user_review",
            "product_creator",
            "product_created_on",
            "is_avaliable",
        ]

    def resolve_current_user_review(self, info):
        user = info.context.user
        current_user_review = None
        if user.is_authenticated:
            current_user_review = Rating.objects.filter(item=self, user=user).first()
        return current_user_review

    def resolve_reviews(self, info):
        item_ratings = Rating.objects.filter(item=self)
        return item_ratings

    def resolve_reviews_count(self, info):
        return Rating.objects.filter(item=self).count()

    def resolve_editable(self, info):
        user = info.context.user
        editable = False
        if (
            user.is_authenticated
            and Vendor.objects.filter(user=user.profile).exists()
            and self.product_creator is not None
        ):
            vendor = Vendor.objects.get(user=user.profile)
            # check if other stored have added this item
            if vendor.store == self.product_creator.store:
                # get all the stores that have this item and exclude the current store
                stores = self.product_avaliable_in.exclude(
                    store_nickname=self.product_creator.store
                )
                if stores.count() > 0:
                    editable = False
                else:
                    editable = True

        return editable

    def resolve_average_rating(self, info):
        return self.average_rating

    def resolve_product_share_visibility(self, info):
        user = info.context.user
        product_share_visibility = self.product_share_visibility
        # check if the user is authenticated
        if (
            user.is_authenticated
            and Vendor.objects.filter(user=user.profile).exists()
            and self.product_creator is not None
        ):
            # check if the user is a vendor
            vendor = Vendor.objects.get(user=user.profile)
            # check if the vendor is the creator of the product
            if vendor.store == self.product_creator.store:
                product_share_visibility = "PUBLIC"
        return product_share_visibility

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

    def resolve_avaliable_store(self, info, store_nickname=None):
        store = None
        if store_nickname:
            store = self.product_avaliable_in.filter(
                store_nickname=store_nickname
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


class ShippingType(graphene.ObjectType):
    sch = graphene.String()
    address = graphene.String()
    batch = graphene.String()


class ShippingInputType(graphene.InputObjectType):
    sch = graphene.String()
    address = graphene.String()
    batch = graphene.String()


class TotalOrder:
    price = graphene.Int()
    platePrice = graphene.Int()


class CountOrder:
    items = graphene.Int()
    plate = graphene.Int()


class TotalOrderType(TotalOrder, graphene.ObjectType):
    pass


class TotalOrderInputType(TotalOrder, graphene.InputObjectType):
    pass


class CountOrderType(CountOrder, graphene.ObjectType):
    pass


class CountOrderInputType(CountOrder, graphene.InputObjectType):
    pass


class StoreInfoType(graphene.ObjectType):
    id = graphene.ID(required=True)
    storeId = graphene.String(required=True)
    total = graphene.Field(TotalOrderType, required=True)
    count = graphene.Field(CountOrderType, required=True)
    items = graphene.List(JSONField, required=True)

    store = graphene.Field(StoreType)

    def resolve_store(self, info):
        return Store.objects.filter(store_nickname=self.get("storeId")).first()


class StoreInfoInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    storeId = graphene.String(required=True)
    total = TotalOrderInputType(required=True)
    count = CountOrderInputType(required=True)
    items = graphene.List(JSONField, required=True)


class OrderType(DjangoObjectType):
    shipping = graphene.Field(ShippingType, default_value=None)
    stores_infos = graphene.List(StoreInfoType, default_value=None)

    class Meta:
        model = Order
        fields = [
            "id",
            "overall_price",
            "delivery_fee",
            "shipping",
            "stores_infos",
            "linked_items",
            "order_status",
            "order_payment_currency",
            "order_payment_status",
            "created_on",
            "updated_on",
        ]

    def resolve_id(self, info):
        return self.order_track_id

    def resolve_shipping(self, info):
        shipping = json.loads(self.shipping)
        return ShippingType(
            sch=shipping["sch"], address=shipping["address"], batch=shipping["batch"]
        )

    def resolve_stores_infos(self, info):
        stores_infos = json.loads(self.stores_infos)

        return stores_infos
