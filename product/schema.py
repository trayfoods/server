import graphene
from graphql import GraphQLError
from product.types import ItemAttributeType
from product.mutations import (
    AddAvaliableProductMutation,
    AddProductMutation,
    AddProductClickMutation,
    CreateOrderMutation,
    RateItemMutation,
    HelpfulReviewMutation,
    InitializeTransactionMutation,
    UpdateItemMenuMutation,
)
from product.models import Item, ItemAttribute

from product.queries.item import ItemQueries
from product.queries.order import OrderQueries


class Query(ItemQueries, OrderQueries, graphene.ObjectType):
    all_item_attributes = graphene.List(ItemAttributeType)
    item_attributes = graphene.List(ItemAttributeType, _type=graphene.Int())
    item_attribute = graphene.Field(ItemAttributeType, urlParamName=graphene.String())

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
    update_item_menu = UpdateItemMenuMutation.Field()
    create_order = CreateOrderMutation.Field()
    rate_item = RateItemMutation.Field()
    helpful_review = HelpfulReviewMutation.Field()
    initialize_transaction = InitializeTransactionMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
