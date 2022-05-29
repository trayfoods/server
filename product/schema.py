import graphene
from graphql import GraphQLError
from product.types import ItemType, ItemAttributeType
from product.mutations import EditAvaliableProductsMutation, AddProductMutation
from product.models import Item, ItemAttribute


class Query(graphene.ObjectType):
    all_items = graphene.List(ItemType)
    items = graphene.List(ItemType, count=graphene.Int())
    item = graphene.Field(ItemType, item_id=graphene.Int())

    all_item_attributes = graphene.List(ItemAttributeType)
    item_attributes = graphene.List(ItemAttributeType, _type=graphene.Int())
    item_attribute = graphene.Field(
        ItemAttributeType, urlParamName=graphene.String())

    def resolve_all_items(self, info, **kwargs):
        return Item.objects.all()

    def resolve_items(self, info, count):
        count = count + 1
        items = Item.objects.all()
        if items.count() >= count:
            items = items[:count]
        return items

    def resolve_item(self, info, item_id):
        item = Item.objects.filter(pk=item_id).first()
        if item is None:
            raise GraphQLError("404: Item Not Found")
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
    avaliable_products = EditAvaliableProductsMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
