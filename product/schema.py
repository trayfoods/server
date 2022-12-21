import graphene
from graphql import GraphQLError
from product.types import ItemType, ItemAttributeType
from product.mutations import (AddAvaliableProductMutation,
                               AddMultipleAvaliableProductsMutation, AddProductMutation, AddProductClickMutation)
from product.models import Item, ItemAttribute
from product.utils import recommend_items
from users.models import UserActivity
from trayapp.custom_model import ItemsAvalibilityNode
# basic searching
from django.db.models import Q


class Query(graphene.ObjectType):
    hero_data = graphene.List(ItemType, count=graphene.Int(required=False))
    items = graphene.List(ItemType, count=graphene.Int(required=False))
    item = graphene.Field(ItemType, item_slug=graphene.String())

    item_attributes = graphene.List(ItemAttributeType, _type=graphene.Int())
    item_attribute = graphene.Field(
        ItemAttributeType, urlParamName=graphene.String())

    search_items = graphene.List(ItemType, query=graphene.String(
        required=True), count=graphene.Int(required=False))

    check_muliple_items_is_avaliable = graphene.List(
        ItemsAvalibilityNode, items_slug_store_nickName=graphene.String(required=True))

    def resolve_check_muliple_items_is_avaliable(self, info, items_slug_store_nickName):
        list_of_items = []
        if items_slug_store_nickName.find(">") > -1 and items_slug_store_nickName.find(",") > -1:
            list_of_items_str = items_slug_store_nickName.split(",")
            if list_of_items_str:
                for item_str in list_of_items_str:
                    if item_str != "":
                        item_slug, store_nickName = item_str.split(">")
                        item = Item.objects.filter(
                            product_slug=item_slug).first()
                        if not item is None:
                            new_item = {
                                "product_slug": item.product_slug,
                                "store_avaliable_in": item.product_avaliable_in.all(),
                                "is_avaliable": False,
                                "avaliable_store": store_nickName
                            }
                            store_checker = item.product_avaliable_in.filter(
                                store_nickname=store_nickName).first()
                            if store_checker:
                                new_item = {
                                    "product_slug": item.product_slug,
                                    "store_avaliable_in": item.product_avaliable_in.all(),
                                    "is_avaliable": True,
                                    "avaliable_store": store_checker.store_nickname
                                }
                            list_of_items.append(new_item)
        return list_of_items

    def resolve_search_items(self, info, query, count=None):
        filtered_items = Item.objects.filter(Q(product_name__icontains=query) | Q(
            product_desc__icontains=query) | Q(product_slug__iexact=query))
        if count:
            count = count + 1
            if filtered_items.count() >= count:
                filtered_items = filtered_items[:count]
        else:
            filtered_items = filtered_items[:20]
        return filtered_items

    def resolve_hero_data(self, info, count=None):
        items = Item.objects.filter(product_type__urlParamName__icontains="dish").exclude(
            product_type__urlParamName__icontains="not").order_by("-product_clicks")
        if count:
            count = count + 1
            if items.count() >= count:
                items = items[:count]
        return items

    def resolve_items(self, info, count=None):
        if self.context.user.is_authenticated:
            items = Item.objects.all().distinct()
            if UserActivity.objects.filter(user_id=info.context.user.id).count() > 2:
                items = recommend_items(self.context.user.id)
        else:
            items = Item.objects.all().distinct()
        if count:
            count = count + 1
            if items.count() >= count:
                items = items[:count]
        return items

    def resolve_item(self, info, item_slug):
        item = Item.objects.filter(product_slug=item_slug).first()
        if not item is None:
            item.product_views += 1
            item.save()
        else:
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
    add_product_click = AddProductClickMutation.Field()
    add_available_product = AddAvaliableProductMutation.Field()
    add_available_products = AddMultipleAvaliableProductsMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
