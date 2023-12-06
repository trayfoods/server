import graphene
from graphene_django.filter import DjangoFilterConnectionField
from users.models import Store
from users.types import StoreType, StoreNode


class StoreQueries(graphene.ObjectType):
    stores = DjangoFilterConnectionField(StoreNode)
    get_store = graphene.Field(StoreType, store_nickname=graphene.String())

    def resolve_stores(self, info, **kwargs):
        return Store.objects.all().exclude(is_active=False)

    def resolve_get_store(self, info, store_nickname):
        user = info.context.user
        store = Store.objects.filter(store_nickname=store_nickname).first()
        if user.is_authenticated:
            if store.vendor == user.profile:
                return store

        if not store.is_active:
            return None

        if not store is None:
            store.store_rank += 0.5
            store.save()
        return store

    def resolve_get_trending_stores(self, info, page, count=None, page_size=10):
        from trayapp.utils import paginate_queryset

        """
        Resolve the get_trending_stores query.

        Args:
            info: The GraphQL ResolveInfo object.
            page: The page number for pagination.
            count: The maximum number of stores to return.
            page_size: The number of stores to display per page.

        Returns:
            A paginated queryset of trending stores.
        """
        stores_list = Store.objects.all().order_by("-store_rank")
        # check if each store products are up to 2
        for store in stores_list:
            if store.store_products.count() < 2:
                stores_list = stores_list.exclude(pk=store.pk)
        if count is not None:
            if stores_list.count() >= count:
                stores_list = stores_list[:count]
        else:
            stores_list = stores_list
        paginated_queryset = paginate_queryset(stores_list, page_size, page)
        return paginated_queryset
