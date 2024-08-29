import graphene
from graphene_django.filter import DjangoFilterConnectionField
from users.models import Store, Profile, Student
from product.models import Order
from users.types import StoreType, StoreNode, StoreItmMenuType, MenuType
from product.types import ItemNode, CategoryType, ItemAttribute
from trayapp.permissions import permission_checker, IsAuthenticated
from graphql import GraphQLError

from django.utils import timezone


class StoreQueries(graphene.ObjectType):
    stores = DjangoFilterConnectionField(StoreNode)
    store_items = DjangoFilterConnectionField(ItemNode)
    menu = graphene.Field(MenuType, name=graphene.String(required=True))
    store_items_menus = graphene.List(StoreItmMenuType)
    store_items_categories = graphene.List(
        CategoryType, store_nickname=graphene.String()
    )
    top10_store_items = graphene.List(ItemNode, store_nickname=graphene.String())
    get_store = graphene.Field(StoreType, store_nickname=graphene.String())
    featured_stores = graphene.List(StoreType)

    @permission_checker([IsAuthenticated])
    def resolve_featured_stores(self, info):
        """
        Featured Store
        - get user country
        """
        featured_stores = []
        profile: Profile = info.context.user.profile
        country = profile.country
        state = profile.state
        city = profile.city

        regional_stores = (
            Store.filter_by_country(country)
            .exclude(is_approved=False, vendor=profile)
            .filter(state=state)
            .filter(city=city)
        )[:5]

        filtered_stores = []
        if profile.is_student:
            student: Student = profile.student
            school = student.school
            campus = student.campus

            filtered_stores = (
                Store.objects.filter(school=school, campus=campus)
                .exclude(is_approved=False, vendor=profile)
                .order_by("-store_rank")[:5]
            )

        # get user orders for 14 days
        user_orders = Order.objects.filter(
            user=profile, order_status="delivered"
        ).filter(
            created_at__date__gte=timezone.now().date() - timezone.timedelta(days=14)
        )

        # get linked stores
        linked_stores = []
        for order in user_orders:
            linked_stores.append(order.linked_stores.all().exclude(is_approved=False, vendor=profile))

        linked_stores = list(set(linked_stores))
        linked_stores = [
            store for store in linked_stores if store and store.is_approved
        ]

        # merge all stores
        featured_stores = list(
            set(list(regional_stores) + list(filtered_stores) + list(linked_stores))
        )

        # sort the list by store rank in descending order
        featured_stores = sorted(
            featured_stores, key=lambda x: -x.store_rank, reverse=True
        )

        # filter out closed stores with store.get_is_open_data()
        featured_stores = [
            store
            for store in featured_stores
            if store.get_is_open_data().get("is_open") == True
        ]

        # get top 5 stores
        featured_stores = featured_stores[:5]

        return featured_stores

    def resolve_stores(self, info, **kwargs):
        stores = Store.objects.all().exclude(is_approved=False)

        user = info.context.user
        if user.is_authenticated:
            user_gender = user.profile.gender
            stores = stores.filter(gender_preference=user_gender) | stores.filter(
                gender_preference__isnull=True
            )
        return stores

    @permission_checker([IsAuthenticated])
    def resolve_store_items(self, info, **kwargs):
        user = info.context.user
        if not "VENDOR" in user.roles:
            raise GraphQLError("You are not a vendor")
        store: Store = user.profile.store
        return store.get_store_products()

    @permission_checker([IsAuthenticated])
    def resolve_store_items_menus(self, info, **kwargs):
        user = info.context.user
        if not "VENDOR" in user.roles:
            raise GraphQLError("You are not a vendor")

        store: Store = user.profile.store
        store_items = store.get_store_products()
        store_menu = store.menus()
        store_menu_with_items = []

        for menu in store_menu:
            store_menu_with_items.append(
                StoreItmMenuType(menu=menu, items=store_items.filter(product_menu=menu))
            )
        return store_menu_with_items

    def resolve_store_items_categories(self, info, store_nickname):
        store_qs = Store.objects.filter(store_nickname=store_nickname)
        if not store_qs.exists():
            raise GraphQLError(
                "Store was not found to get top 10 items, please contact support"
            )
        store = store_qs.first()

        store_items = store.get_store_products()

        # get all items categories in one list without duplicates
        store_items_categories = []
        images_used_in_categories = []
        for item in store_items:
            item_images = item.product_images.all()
            for category in item.product_categories.all():
                item_image = ""
                # get the first image that is not used in another category
                for image in item_images:
                    if image.item_image.url not in images_used_in_categories:
                        item_image = image.item_image.url
                        images_used_in_categories.append(item_image)
                        break
                category_instance: ItemAttribute = category
                category = {
                    "name": category_instance.name,
                    "slug": category_instance.slug,
                    "img": info.context.build_absolute_uri(item_image),
                }
                if category not in store_items_categories:
                    store_items_categories.append(category)

        # check for duplicates by slug and remove them
        # keep the one with an image if the other does not have
        store_items_categories = [
            dict(t) for t in {tuple(d.items()) for d in store_items_categories}
        ]

        return store_items_categories

    def resolve_top10_store_items(self, info, store_nickname):
        top_store_items = []
        store_qs = Store.objects.filter(store_nickname=store_nickname)
        if not store_qs.exists():
            raise GraphQLError(
                "Store was not found to get top 10 items, please contact support"
            )
        store = store_qs.first()
        # filter store items and exclude packages
        store_items = store.get_store_products().exclude(
            product_menu__type__slug__icontains="package"
        )

        top_store_items = store_items.order_by("-product_views")[:11]

        return top_store_items

    def resolve_get_store(self, info, store_nickname):
        user = info.context.user
        store = Store.objects.filter(store_nickname=store_nickname).first()
        if user.is_authenticated:
            if store.vendor == user.profile:
                return store

            if (
                store.gender_preference
                and user.profile.gender != store.gender_preference
            ):
                return None

        if not store.is_approved:
            return None

        if not store is None:
            store.store_rank += 0.5
            store.save()
        return store
