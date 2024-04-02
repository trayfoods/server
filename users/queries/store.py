import graphene
from graphene_django.filter import DjangoFilterConnectionField
from users.models import Store
from users.types import StoreType, StoreNode, StoreItmMenuType
from product.types import ItemNode
from trayapp.permissions import permission_checker, IsAuthenticated
from graphql import GraphQLError


class StoreQueries(graphene.ObjectType):
    stores = DjangoFilterConnectionField(StoreNode)
    store_items = DjangoFilterConnectionField(ItemNode)
    store_itm_menu = graphene.List(StoreItmMenuType)
    top10_store_items = graphene.List(ItemNode, store_nickname=graphene.String())
    get_store = graphene.Field(StoreType, store_nickname=graphene.String())

    def resolve_stores(self, info, **kwargs):
        return Store.objects.all().exclude(is_approved=False)

    @permission_checker([IsAuthenticated])
    def resolve_store_items(self, info, **kwargs):
        user = info.context.user
        if not "VENDOR" in user.roles:
            raise GraphQLError("243: You are not a vendor")
        store: Store = user.profile.store
        return store.get_store_products()

    @permission_checker([IsAuthenticated])
    def resolve_store_itm_menu(self, info, **kwargs):
        user = info.context.user
        if not "VENDOR" in user.roles:
            raise GraphQLError("243: You are not a vendor")

        store: Store = user.profile.store
        store_items = store.get_store_products()
        store_menu = store.store_menu
        store_menu_with_items = []

        for menu in store_menu:
            store_menu_with_items.append(
                StoreItmMenuType(
                    menu=menu, items=store_items.filter(store_menu_name=menu)
                )
            )
        return store_menu_with_items

    def resolve_top10_store_items(self, info, store_nickname):
        top_store_items = []
        store_qs = Store.objects.filter(store_nickname=store_nickname)
        if not store_qs.exists():
            raise GraphQLError(
                "Store was not found to get top 10 items, please contact support"
            )
        store = store_qs.first()
        # filter store items
        store_items = store.get_store_products()

        top_store_items = store_items.order_by("-product_views")[:11]

        return top_store_items

    def resolve_get_store(self, info, store_nickname):
        user = info.context.user
        store = Store.objects.filter(store_nickname=store_nickname).first()
        if user.is_authenticated:
            if store.vendor == user.profile:
                return store

        if not store.is_approved:
            return None

        if not store is None:
            store.store_rank += 0.5
            store.save()
        return store
