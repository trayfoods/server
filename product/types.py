import json

import graphene
from graphene_django.types import DjangoObjectType

from trayapp.permissions import permission_checker, IsAuthenticated
from .models import Item, ItemAttribute, ItemImage, Order, Rating
from users.models import Store, DeliveryPerson
from users.types import StoreType, School
from .filters import ItemFilter, OrderFilter, StoreOrderFilter, DeliveryPersonFilter


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
            "product_categories",
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
    sch = graphene.String(default_value=None)
    address = graphene.String()

    def resolve_sch(self, info):
        sch = self.sch
        if sch == None or sch == "":
            return None
        sch = sch.lower().strip()
        sch_name = School.objects.filter(slug=sch).first().name
        return sch_name


class ShippingInputType(graphene.InputObjectType):
    sch = graphene.String(default_value=None)
    address = graphene.String()


class TotalOrder:
    price = graphene.Int()
    plate_price = graphene.Int()


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


class StoreItemPlate:
    idx = graphene.Int(required=True)
    how_much = graphene.Int(required=True)
    plate_num = graphene.Int(required=True)


class StoreItemPlateType(StoreItemPlate, graphene.ObjectType):
    pass


class StoreItemPlateInputType(StoreItemPlate, graphene.InputObjectType):
    pass


class StoreItem:
    product_name = graphene.String(required=True)
    product_slug = graphene.String(required=True)
    product_price = graphene.Int(required=True)
    product_image = graphene.String(required=True)
    product_cart_qty = graphene.Int(required=True)
    # plates =


class StoreItemType(StoreItem, graphene.ObjectType):
    plates = graphene.List(StoreItemPlateType)


class StoreItemInputType(StoreItem, graphene.InputObjectType):
    plates = graphene.List(StoreItemPlateInputType)


class StoreInfo:
    id = graphene.ID(required=True)
    storeId = graphene.String(required=True)
    hasPhysicalStore = graphene.Boolean(required=True)
    items = graphene.List(StoreItemType, required=True)


class StoreInfoType(StoreInfo, graphene.ObjectType):
    total = graphene.Field(TotalOrderType, required=True)
    count = graphene.Field(CountOrderType, required=True)
    items = graphene.List(StoreItemType, required=True)
    store = graphene.Field(StoreType)

    def resolve_store(self, info):
        return Store.objects.filter(id=int(self.get("storeId"))).first()


class StoreInfoInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    storeId = graphene.String(required=True)
    items = graphene.List(StoreItemInputType, required=True)
    total = TotalOrderInputType(required=True)
    count = CountOrderInputType(required=True)


class StoreNote:
    storeId = graphene.String(required=True)
    note = graphene.String(required=True)


class StoreNoteType(StoreNote, graphene.ObjectType):
    pass


class StoreNoteInputType(StoreNote, graphene.InputObjectType):
    pass


class OrderUserType(graphene.ObjectType):
    image = graphene.String(default_value=None)
    calling_code = graphene.String(required=True)
    phone_number = graphene.String(required=True)

    def resolve_image(self, info):
        if not self.image:
            return None
        return info.context.build_absolute_uri(self.image.url)

    def resolve_calling_code(self, info):
        return self.calling_code

    def resolve_phone_number(self, info):
        return self.phone_number


class OrderDeliveryPersonType(OrderUserType, graphene.ObjectType):
    status = graphene.String()
    storeId = graphene.String()


class OrderType(DjangoObjectType):
    shipping = graphene.Field(ShippingType)
    stores_infos = graphene.List(StoreInfoType)
    linked_items = graphene.List(ItemType)
    linked_delivery_people = graphene.List("users.types.DeliveryPersonType")
    view_as = graphene.List(graphene.String)
    user = graphene.Field(OrderUserType, default_value=None)
    items_count = graphene.Int()
    items_images_urls = graphene.List(graphene.String)
    display_date = graphene.String()
    customer_note = graphene.String()
    confirm_pin = graphene.String()
    delivery_people = graphene.List(OrderDeliveryPersonType)
    order_status = graphene.String()

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
            "customer_note",
            "order_track_id",
            "delivery_fee",
            "linked_items",
            "order_status",
            "display_date",
            "overall_price",
            "service_fee",
            "order_payment_currency",
            "order_payment_status",
            "order_payment_url",
            "items_images_urls",
            "confirm_pin",
            "delivery_people",
        ]

    def resolve_id(self, info):
        return self.order_track_id

    def resolve_user(self: Order, info):
        current_user = info.context.user
        order_status = self.get_order_status(current_user.profile)
        view_as = self.view_as(current_user.profile)
        if order_status == "DELIVERED" or order_status == "CANCELLED" or "PENDING":
            return None
        # delivery_people = self.delivery_people
        # if self.user == current_user.profile and len(delivery_people) > 0:
        #     return None
        if len(view_as) > 0:
            return self.user

    def resolve_delivery_people(self, info):
        delivery_people = self.delivery_people
        delivery_people_infos = []
        for delivery_person in delivery_people:
            delivery_person_profile = (
                DeliveryPerson.objects.filter(id=delivery_person["id"]).first().profile
            )
            delivery_people_infos.append(
                OrderDeliveryPersonType(
                    image=delivery_person_profile.image,
                    calling_code=delivery_person_profile.calling_code,
                    phone_number=delivery_person_profile.phone_number,
                    status=delivery_person["status"],
                    storeId=delivery_person["storeId"],
                )
            )

        return delivery_people_infos

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
        shipping = self.shipping
        if shipping:
            shipping = {
                "sch": shipping["sch"],
                "address": shipping["address"],
            }
            return ShippingType(**shipping)

    def resolve_stores_infos(self, info):
        stores_infos = self.stores_infos

        current_user = info.context.user
        current_user_profile = current_user.profile
        view_as = self.view_as(current_user_profile)

        # set all price to 0 if the user is a delivery person
        if "DELIVERY_PERSON" in view_as:
            delivery_person = self.get_delivery_person(
                delivery_person_id=current_user_profile.get_delivery_person().id
            )
            if delivery_person:
                # filter stores_infos to only the store that the delivery person is linked to
                stores_infos = [
                    store_info
                    for store_info in stores_infos
                    if str(store_info["storeId"]) == str(delivery_person["storeId"])
                ]
            for store_info in stores_infos:
                store_info["total"]["price"] = 0
                store_info["total"]["platePrice"] = 0

                # set all item price to 0
                for item in store_info["items"]:
                    item["productPrice"] = 0

        # check if view_as is set to vendor, then return only the store that the vendor is linked to
        if "VENDOR" in view_as:
            current_user_profile = current_user.profile
            stores_infos = [
                store_info
                for store_info in stores_infos
                if str(store_info["storeId"]) == str(current_user_profile.store.id)
            ]  # filter the stores_infos to only the store that the vendor is linked to

        return stores_infos

    def resolve_customer_note(self: Order, info):
        current_user = info.context.user
        current_user_profile = current_user.profile
        view_as = self.view_as(current_user_profile)

        store_notes = self.store_notes
        customer_note = self.delivery_person_note

        # check if view_as is set to VENDOR,
        # then find and return the store note as customer note
        if "VENDOR" in view_as and not "USER" in view_as:
            store_note = [
                store_note
                for store_note in store_notes
                if store_note["storeId"] == current_user_profile.store.id
            ]  # filter the stores_infos to only the store that the vendor is linked to
            if len(store_note) > 0:
                customer_note = store_note[0]["note"]
        return customer_note

    def resolve_linked_items(self, info):
        return self.linked_items.all()

    def resolve_linked_delivery_people(self, info):
        return self.linked_delivery_people.all()

    def resolve_view_as(self, info):
        current_user_profile = info.context.user.profile
        return self.view_as(current_user_profile)

    def resolve_confirm_pin(self, info):
        return self.get_confirm_pin()

    def resolve_order_status(self: Order, info):
        current_user_profile = info.context.user.profile
        return self.get_order_status(current_user_profile)


class DiscoverDeliveryType(OrderType, DjangoObjectType):
    class Meta:
        model = Order

    def resolve_user(self, info):
        return None

    def resolve_confirm_pin(self, info):
        return ""


class OrderNode(OrderType, DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (graphene.relay.Node,)
        filterset_class = OrderFilter


class StoreOrderNode(OrderType, DjangoObjectType):
    items = graphene.List(StoreItemType)

    class Meta:
        model = Order
        interfaces = (graphene.relay.Node,)
        filterset_class = StoreOrderFilter

    @permission_checker([IsAuthenticated])
    def resolve_items(self, info):
        items = []
        # get the current user
        user = info.context.user
        current_user_store_id = user.profile.store.id
        # loop through the stores_infos to get the current store then get the items
        for store_info in self.stores_infos:
            if str(store_info["storeId"]) == str(current_user_store_id):
                items = store_info["items"]
                break
        return items


class DeliveryPersonOrderNode(OrderType, DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (graphene.relay.Node,)
        filterset_class = DeliveryPersonFilter

    def resolve_stores_infos(self, info):
        stores_infos = self.stores_infos

        current_user = info.context.user
        current_user_profile = current_user.profile
        view_as = self.view_as(current_user_profile)

        # set all price to 0 if the user is a delivery person
        if "DELIVERY_PERSON" in view_as:
            delivery_person = self.get_delivery_person(
                delivery_person_id=current_user_profile.get_delivery_person().id
            )
            if delivery_person:
                # filter stores_infos to only the store that the delivery person is linked to
                stores_infos = [
                    store_info
                    for store_info in stores_infos
                    if str(store_info["storeId"]) == str(delivery_person["storeId"])
                ]
            for store_info in stores_infos:
                store_info["total"]["price"] = 0
                store_info["total"]["platePrice"] = 0

                # set all item price to 0
                for item in store_info["items"]:
                    item["productPrice"] = 0

        return stores_infos
