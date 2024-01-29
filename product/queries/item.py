import graphene
from graphql import GraphQLError

from ..models import Item
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

    item_reviews = DjangoFilterConnectionField(ReviewNode, item_slug=graphene.String(required=True))

    def resolve_items(self, info, **kwargs):
        return Item.get_items().exclude(product_creator__is_approved=False)

    def resolve_hero_data(self, info):
        items = (
            Item.get_items()
            .exclude(product_creator__is_approved=False)
            .filter(product_type__slug__icontains="dish")
            .exclude(product_type__slug__icontains="not")
            .order_by("-product_clicks")[:4]
        )
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
