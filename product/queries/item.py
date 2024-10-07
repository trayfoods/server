import graphene
from graphql import GraphQLError

from ..models import Item
from users.models import Store, Menu
from ..types import ItemNode, ItemType, ReviewNode
from users.models import UserActivity
from graphene_django.filter import DjangoFilterConnectionField


class ItemQueries(graphene.ObjectType):
    items = DjangoFilterConnectionField(ItemNode)

    item = graphene.Field(
        ItemType,
        item_slug=graphene.String(required=True),
    )

    hero_data = graphene.List(ItemType)

    item_reviews = DjangoFilterConnectionField(
        ReviewNode, item_slug=graphene.String(required=True)
    )

    def resolve_items(self, info, **kwargs):
        user = info.context.user
        store_nickname = kwargs.get("store_nickname", None)

        # check if store_nickname is provided
        store_instance = None
        if store_nickname:
            # get the store querysets
            store_qs = Store.objects.filter(store_nickname=store_nickname)
            if store_qs.exists():
                store_instance = store_qs.first()

        # check if the user is authenticated and is a vendor and store_nickname is provided
        items = Item.get_items().exclude(product_creator__is_approved=False)
        if (
            user.is_authenticated
            and "VENDOR" in user.roles
            and store_instance == user.profile.store
        ):
            items = Item.get_items_by_store(store_instance)

        # filter items by store's gender preference is equal to user profile gender
        if user.is_authenticated:
            user_gender = user.profile.gender
            items = items.filter(
                product_creator__gender_preference=user_gender
            ) | items.filter(product_creator__gender_preference__isnull=True)

        return items

    def resolve_item(self, info, item_slug):
        from django.utils import timezone

        user = info.context.user
        item = Item.get_items().filter(product_slug=item_slug).first()
        if user.is_authenticated and "VENDOR" in user.roles:
            item_by_store = Item.objects.filter(
                product_slug=item_slug, product_creator=user.profile.store
            )
            if item_by_store.exists():
                item = item_by_store.first()

        if not item is None:
            item.product_views += 1
            item.save()
            if info.context.user.is_authenticated:
                new_activity = UserActivity.objects.create(
                    user_id=info.context.user.id,
                    activity_type="view",
                    item=item,
                    timestamp=timezone.now(),
                )
                new_activity.save()
        else:
            raise GraphQLError("404: Item Not Found")

        return item

    def resolve_menu(self, info, name):
        menu = Menu.objects.filter(name=name).first()
        if menu is None:
            raise GraphQLError("Menu does not exist")
        return menu

    def resolve_hero_data(self, info):
        # filter items by store's gender preference is equal to user profile gender
        user = info.context.user
        items = Item.get_items()
        if user.is_authenticated:
            user_gender = user.profile.gender
            items = items.filter(
                product_creator__gender_preference=user_gender
            ) | Item.get_items().filter(product_creator__gender_preference__isnull=True)

        items = (
            items.exclude(product_creator__is_approved=False)
            .filter(product_menu__type__slug__icontains="food")
            .exclude(product_menu__type__slug__icontains="not")
            .order_by("-product_clicks")[:4]
        )

        return items
