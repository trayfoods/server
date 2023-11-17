import graphene
from graphql import GraphQLError

from ..models import Item
from ..types import ItemNode, ItemType
from users.models import UserActivity
from graphene_django.filter import DjangoFilterConnectionField

class ItemQueries(graphene.ObjectType):
    items = DjangoFilterConnectionField(
        ItemNode
    )

    item = graphene.Field(
        ItemType,
        item_slug=graphene.String(required=True),
        store_nickname=graphene.String(required=False),
    )

    def resolve_item(self, info, item_slug, store_nickname=None):
        from django.utils import timezone
        
        item = Item.objects.filter(product_slug=item_slug).first()
        if not item is None:
            # check if item is avaliable in the store if store_nickname is provided
            if (
                not store_nickname is None
                and not item.product_avaliable_in.filter(
                    store_nickname=store_nickname
                ).count()
                > 0
            ):
                raise GraphQLError("404: Item Not Avaliable in Store")

            item.product_views += 1
            item.save()
            if info.context.user.is_authenticated:
                new_activity = UserActivity.objects.create(
                    user_id=info.context.user.id,
                    activity_message=None,
                    activity_type="view",
                    item=item,
                    timestamp=timezone.now(),
                )
                new_activity.save()
        else:
            raise GraphQLError("404: Item Not Found")

        return item
