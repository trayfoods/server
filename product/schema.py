import graphene
from graphql import GraphQLError
from product.types import ItemType, ItemAttributeType
from product.mutations import (AddAvaliableProductMutation,
                               AddMultipleAvaliableProductsMutation, AddProductMutation, AddProductClickMutation)
from product.models import Item, ItemAttribute

# basic searching
from django.db.models import Q


class Query(graphene.ObjectType):
    hero_data = graphene.List(ItemType, count=graphene.Int(required=False))
    items = graphene.List(ItemType, count=graphene.Int(required=False))
    item = graphene.Field(ItemType, item_slug=graphene.String())

    item_attributes = graphene.List(ItemAttributeType, _type=graphene.Int())
    item_attribute = graphene.Field(
        ItemAttributeType, urlParamName=graphene.String())

    search_items = graphene.List(ItemType, query=graphene.String())

    def resolve_search_items(self, info, query):
        filtered_items = Item.objects.filter(
            Q(product_name__icontains=query) | Q(product_desc__icontains=query) | Q(product_slug__iexact=query))[:5]
        return filtered_items

    def resolve_hero_data(self, info, count=None):
        items = Item.objects.filter(product_type__urlParamName__icontains="dish").order_by("-product_views")
        if count:
            count = count + 1
            if items.count() >= count:
                items = items[:count]
        return items

    def resolve_items(self, info, count=None):
        items = Item.objects.all().distinct()
        if count:
            count = count + 1
            if items.count() >= count:
                items = items[:count]
        return items

    def resolve_item(self, info, item_slug):
        item = Item.objects.filter(product_slug=item_slug.strip()).first()
        if item is None:
            raise GraphQLError("404: Item Not Found")
        item.product_views += 1
        item.save()
        return item

    def resolve_all_item_attributes(self, info, **kwargs):
        return ItemAttribute.objects.all()

    def resolve_item_attributes(self, info, _type):
        if _type == 0:
            _type = "TYPE"
        elif _type == 1:
            _type = "CATEGORY"
        else:
            raise GraphQLError(
                "Please enter either 0 or 1 for types and categories respectively")
        item_attributes = ItemAttribute.objects.filter(_type=_type)
        return item_attributes

    def resolve_item_attribute(self, info, urlParamName):
        item_attribute = ItemAttribute.objects.filter(
            urlParamName=urlParamName).first()
        return item_attribute


class Mutation(graphene.ObjectType):
    add_product = AddProductMutation.Field()
    add_product_click = AddProductClickMutation.Field()
    add_avaliable_product = AddAvaliableProductMutation.Field()
    add_avaliable_products = AddMultipleAvaliableProductsMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
