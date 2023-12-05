import json

import graphene
from graphene_django.types import DjangoObjectType
from .models import Item, ItemAttribute, ItemImage, Order, Rating
from users.models import Store
from users.types import StoreType
from .filters import ItemFilter, OrderFilter

from trayapp.custom_model import JSONField


class ItemImageType(DjangoObjectType):
    product_image = graphene.String()

    class Meta:
        model = ItemImage
        fields = ["id", "product_image", "is_primary"]

    def resolve_product_image(self, info, *args, **kwargs):
        product_image = info.context.build_absolute_uri(self.item_image.url)
        return product_image


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
    average_rating = graphene.Float()
    reviews = graphene.List(ReviewsType)
    reviews_count = graphene.Int()
    current_user_review = graphene.Field(ReviewsType)
    is_avaliable_for_store = graphene.String()

    class Meta:
        model = Item
        fields = [
            "id",
            "product_name",
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
            "has_qty",
            "average_rating",
            "reviews",
            "reviews_count",
            "current_user_review",
            "product_creator",
            "product_created_on",
            "is_avaliable",
            "store_menu_name",
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

    def resolve_average_rating(self, info):
        return self.average_rating

    def resolve_product_share_visibility(self, info):
        user = info.context.user
        product_share_visibility = self.product_share_visibility
        # check if the user is authenticated
        if not user.is_authenticated:
            return product_share_visibility

        # check if the user is the creator of the product
        if (
            user.profile.store
            and self.product_creator
            and (user.profile.store == self.product_creator)
        ):
            product_share_visibility = "PUBLIC"
        return product_share_visibility

    def resolve_product_qty(self, info):
        product_qty = self.product_qty
        if product_qty == 0:
            product_qty = 1
        return product_qty

    def resolve_is_avaliable_for_store(self, info):
        user = info.context.user
        store_item = "not_login"
        if user.is_authenticated:
            store_item = "not_vendor"
            vendor = user.profile
            if not vendor.store is None:
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
        return self.is_avaliable


class ItemNode(ItemType, DjangoObjectType):
    class Meta:
        model = Item
        interfaces = (graphene.relay.Node,)
        filterset_class = ItemFilter


class ShippingType(graphene.ObjectType):
    sch = graphene.String()
    address = graphene.String()
    batch = graphene.String()


class ShippingInputType(graphene.InputObjectType):
    sch = graphene.String(default_value=None)
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
    shipping = graphene.Field(ShippingType)
    stores_infos = graphene.List(StoreInfoType)
    linked_items = graphene.List(ItemType)
    view_as = graphene.List(graphene.String)
    user = graphene.Field("users.types.ProfileType", default_value=None)
    items_count = graphene.Int()
    items_images_urls = graphene.List(graphene.String)
    display_date = graphene.String()

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "view_as",
            "shipping",
            "updated_at",
            "created_at",
            "items_count",
            "stores_infos",
            "order_track_id",
            "delivery_fee",
            "linked_items",
            "order_status",
            "display_date",
            "overall_price",
            "transaction_fee",
            "order_payment_currency",
            "order_payment_status",
            "order_payment_url",
            "items_images_urls",
        ]

    def resolve_id(self, info):
        return self.order_track_id

    def resolve_user(self, info):
        current_user = info.context.user
        if self.user != current_user.profile:
            return self.user

    def resolve_display_date(self, info):
        from trayapp.utils import convert_time_to_ago

        return convert_time_to_ago(self.created_at)

    def resolve_items_count(self, info):
        return self.linked_items.count()

    def resolve_items_images_urls(self, info):
        images_urls = []
        for item in self.linked_items.all():
            images_urls.append(
                info.context.build_absolute_uri(
                    item.product_images.first().item_image.url
                )
            )
        return images_urls

    def resolve_shipping(self, info):
        shipping = json.loads(self.shipping)
        sch = None
        if shipping["sch"]:
            sch = shipping["sch"]
        return ShippingType(
            sch=sch, address=shipping["address"], batch=shipping["batch"]
        )

    def resolve_stores_infos(self, info):
        stores_infos = json.loads(self.stores_infos)

        view_as = []
        current_user = info.context.user
        if self.user != current_user.profile:
            view_as = current_user.roles

        # check if view_as is set to vendor, then return only the store that the vendor is linked to
        if "VENDOR" in view_as:
            current_user = info.context.user
            if "VENDOR" in current_user.roles:
                current_user_profile = current_user.profile
                stores_infos = [
                    store_info
                    for store_info in stores_infos
                    if store_info["storeId"]
                    == current_user_profile.store.store_nickname
                ]  # filter the stores_infos to only the store that the vendor is linked to

        return stores_infos

    def resolve_linked_items(self, info):
        return self.linked_items.all()

    def resolve_view_as(self, info):
        current_user = info.context.user
        if self.user != current_user.profile:
            return current_user.roles
        return []


class OrderNode(OrderType, DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (graphene.relay.Node,)
        filterset_class = OrderFilter
