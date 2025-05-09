import graphene
from graphql import GraphQLError
from product.types import ItemAttributeType
from product.mutations import (
    ItemCopyDeleteMutation,
    CreateUpdateItemMutation,
    AddProductClickMutation,
    CreateOrderMutation,
    RateItemMutation,
    HelpfulReviewMutation,
    InitializeTransactionMutation,
    UpdateItemMenuMutation,
    MarkOrderAsMutation,
    AddOrdersStoresSeenMutation,
)
from product.models import ItemAttribute

from product.queries.item import ItemQueries
from product.queries.order import OrderQueries
from product.queries.reviews import ReviewsQueries
from product.queries.store import StoreQueries


class Query(
    ItemQueries, ReviewsQueries, OrderQueries, StoreQueries, graphene.ObjectType
):
    all_item_attributes = graphene.List(ItemAttributeType)
    item_attributes = graphene.List(ItemAttributeType, _type=graphene.Int())
    item_attribute = graphene.Field(ItemAttributeType, slug=graphene.String())

    def resolve_all_item_attributes(self, info, **kwargs):
        food_categories = [
            "Snack",
            "Soup",
            "Swallow",
            "Shawarma",
            "Stew",
            "Rice",
            "Pasta",
            "Bread",
            "Cake",
            "Meat",
            "Fish",
            "Chicken",
            "Turkey",
            "Beef",
            "Pork",
            "Zero Sugar",
            "Juice",
            "Beverage",
            "Dessert",
            "Smoothie",
            "Fruit",
            "Vegetable",
            "Energy Drink",
        ]
        food_categories.sort()
        item_attributes = ItemAttribute.objects.filter(_type="CATEGORY")
        if item_attributes.count() > 0:
            pass
        else:  # create item attributes
            for food_category in food_categories:
                new_item_attribute = ItemAttribute.objects.create(
                    name=food_category,
                    _type="CATEGORY",
                    slug=food_category.replace(" ", "-").lower(),
                )
                new_item_attribute.save()
            item_attributes = ItemAttribute.objects.all()

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

    def resolve_item_attribute(self, info, slug):
        item_attribute = ItemAttribute.objects.filter(slug=slug).first()
        return item_attribute


class Mutation(graphene.ObjectType):
    # product
    create_update_item = CreateUpdateItemMutation.Field()
    add_product_click = AddProductClickMutation.Field()
    copy_delete_item = ItemCopyDeleteMutation.Field()

    # store menu
    update_item_menu = UpdateItemMenuMutation.Field()

    # rating
    rate_item = RateItemMutation.Field()
    helpful_review = HelpfulReviewMutation.Field()

    # order
    create_order = CreateOrderMutation.Field()
    initialize_transaction = InitializeTransactionMutation.Field()
    mark_order_as = MarkOrderAsMutation.Field()
    add_orders_profiles_seen = AddOrdersStoresSeenMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
