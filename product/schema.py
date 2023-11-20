import graphene
from graphql import GraphQLError
from product.types import ItemType, ItemAttributeType, OrderType
from product.mutations import (
    AddAvaliableProductMutation,
    AddMultipleAvaliableProductsMutation,
    AddProductMutation,
    AddProductClickMutation,
    CreateOrderMutation,
    RateItemMutation,
    HelpfulReviewMutation,
    InitializeTransactionMutation,
)
from product.models import Item, ItemAttribute, Order
from trayapp.custom_model import ItemsAvalibilityNode

from product.queries.item import ItemQueries

# basic searching
from django.db.models import Q


class Query(ItemQueries, graphene.ObjectType):
    hero_data = graphene.List(ItemType, count=graphene.Int(required=False))

    user_orders = graphene.List(
        OrderType,
        page=graphene.Int(required=True),
        per_page=graphene.Int(required=False),
    )
    store_orders = graphene.List(
        OrderType,
        page=graphene.Int(required=True),
        per_page=graphene.Int(required=False),
    )

    all_item_attributes = graphene.List(ItemAttributeType)
    item_attributes = graphene.List(ItemAttributeType, _type=graphene.Int())
    item_attribute = graphene.Field(ItemAttributeType, urlParamName=graphene.String())

    check_muliple_items_is_avaliable = graphene.List(
        ItemsAvalibilityNode, items_slug_store_nickName=graphene.String(required=True)
    )

    get_order = graphene.Field(OrderType, order_id=graphene.String(required=True))

    def resolve_user_orders(self, info, page, per_page=20):
        user = info.context.user
        if user.is_authenticated:
            orders = user.orders.all()
            # pagination
            if page:
                return orders[(page - 1) * 20 : per_page * per_page]
            return orders
        else:
            raise GraphQLError("You are not authenticated")

    def resolve_store_orders(self, info, page, per_page=20):
        user = info.context.user
        if user.is_authenticated and user.profile.is_vendor:
            user_store = user.profile.store
            # get all orders for the store
            orders = user_store.orders.all()
            # pagination
            if page:
                return orders[(page - 1) * per_page : page * per_page]
            return orders
        else:
            raise GraphQLError("You are not authenticated")

    def resolve_get_order(self, info, order_id):
        user = info.context.user
        if user.is_authenticated:
            allowed_view_as_roles = ["DELIVERY_PERSON", "VENDOR"]
            
            order = user.orders.filter(order_track_id=order_id).first()

            if user.role in allowed_view_as_roles:
                current_user_profile = user.profile
                order_qs = Order.objects.filter(order_track_id=order_id).first()

                if user.role == allowed_view_as_roles[0] and order_qs.delivery_person.profile == current_user_profile:
                    pass
                elif user.role == allowed_view_as_roles[1] and order_qs.linked_stores.filter(vendor=current_user_profile).exists():
                    pass
                else:
                    order = None

            if order:
                return order
            else:
                raise GraphQLError("Order Not Found")
        else:
            raise GraphQLError("You are not authenticated")

    def resolve_check_muliple_items_is_avaliable(self, info, items_slug_store_nickName):
        list_of_items = []
        if (
            items_slug_store_nickName.find(">") > -1
            and items_slug_store_nickName.find(",") > -1
        ):
            list_of_items_str = items_slug_store_nickName.split(",")
            if list_of_items_str:
                for item_str in list_of_items_str:
                    if item_str != "":
                        item_slug, store_nickName = item_str.split(">")
                        item = Item.objects.filter(product_slug=item_slug).first()
                        if not item is None:
                            new_item = {
                                "product_slug": item.product_slug,
                                "store_avaliable_in": item.product_avaliable_in.all(),
                                "is_avaliable": False,
                                "avaliable_store": store_nickName,
                            }
                            store_checker = item.product_avaliable_in.filter(
                                store_nickname=store_nickName
                            ).first()
                            if store_checker:
                                new_item = {
                                    "product_slug": item.product_slug,
                                    "store_avaliable_in": item.product_avaliable_in.all(),
                                    "is_avaliable": True,
                                    "avaliable_store": store_checker.store_nickname,
                                }
                            list_of_items.append(new_item)
        return list_of_items

    def resolve_hero_data(self, info, count=None):
        items = (
            Item.objects.filter(product_type__urlParamName__icontains="dish")
            .exclude(product_type__urlParamName__icontains="not")
            .order_by("-product_clicks")
        )
        if count:
            count = count + 1
            if items.count() >= count:
                items = items[:count]
        return items

    def resolve_all_item_attributes(self, info, **kwargs):
        food_categories = [
            "Fast Food",
            "Asian Cuisine",
            "Italian Cuisine",
            "American Cuisine",
            "Mexican Cuisine",
            "Healthy and Salad Options",
            "Desserts and Sweets",
            "Breakfast and Brunch",
            "Middle Eastern Cuisine",
            "Beverages",
        ]
        item_types = [
            "Dish",
            "Not Dish",
        ]
        item_attributes = ItemAttribute.objects.all()
        if item_attributes.count() > 0:
            pass
        else:  # create item attributes
            for food_category in food_categories:
                new_item_attribute = ItemAttribute.objects.create(
                    name=food_category,
                    _type="CATEGORY",
                    urlParamName=food_category.replace(" ", "-").lower(),
                )
                new_item_attribute.save()
            item_attributes = ItemAttribute.objects.all()

            for item_type in item_types:
                new_item_attribute = ItemAttribute.objects.create(
                    name=item_type,
                    _type="TYPE",
                    urlParamName=item_type.replace(" ", "-").lower(),
                )
                new_item_attribute.save()

        return item_attributes

    def resolve_item_attributes(self, info, _type):
        if _type == 0:
            _type = "TYPE"
        elif _type == 1:
            _type = "CATEGORY"
        else:
            raise GraphQLError(
                "Please enter either 0 or 1 for types and categories respectively"
            )
        item_attributes = ItemAttribute.objects.filter(_type=_type)
        return item_attributes

    def resolve_item_attribute(self, info, urlParamName):
        item_attribute = ItemAttribute.objects.filter(urlParamName=urlParamName).first()
        return item_attribute


class Mutation(graphene.ObjectType):
    add_product = AddProductMutation.Field()
    add_product_click = AddProductClickMutation.Field()
    add_available_product = AddAvaliableProductMutation.Field()
    add_available_products = AddMultipleAvaliableProductsMutation.Field()
    create_order = CreateOrderMutation.Field()
    rate_item = RateItemMutation.Field()
    helpful_review = HelpfulReviewMutation.Field()
    initialize_transaction = InitializeTransactionMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
