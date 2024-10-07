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
        profile: Profile = info.context.user.profile
        country, state, city = profile.country, profile.state, profile.city

        # Regional stores
        regional_stores = (
            Store.filter_by_country(country)
            .exclude(is_approved=False, vendor=profile)
            .filter(state=state, city=city, is_approved=True)[:5]
        )

        # Filtered stores for students
        # filtered_stores = []
        # if profile.is_student:
        #     student: Student = profile.student
        #     school, campus = student.school, student.campus

        #     filtered_stores = (
        #         Store.objects.filter(school=school, campus=campus)
        #         .exclude(is_approved=False, vendor=profile)
        #         .order_by("-store_rank")[:5]
        #     )

        # User orders in the last 14 days
        user_orders = Order.objects.filter(
            user=profile,
            order_status="delivered",
            created_at__date__gte=timezone.now().date() - timezone.timedelta(days=14),
        )

        # Linked stores from user orders
        linked_stores = set()
        for order in user_orders:
            linked_stores.update(
                order.linked_stores.exclude(is_approved=False, vendor=profile).filter(
                    is_approved=True
                )
            )

        # Combine all stores
        featured_stores = list(set(regional_stores) | linked_stores)

        # Filter out closed stores
        featured_stores = [
            store
            for store in featured_stores
            if store.get_is_open_data().get("is_open")
        ]

        # Sort by store rank in descending order and get top 5
        return sorted(featured_stores, key=lambda x: -x.store_rank)[:5]

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
        if "VENDOR" not in user.roles:
            raise GraphQLError("You are not a vendor")
        store: Store = user.profile.store
        return store.get_store_products()

    @permission_checker([IsAuthenticated])
    def resolve_store_items_menus(self, info, **kwargs):
        user = info.context.user
        if "VENDOR" not in user.roles:
            raise GraphQLError("You are not a vendor")

        store: Store = user.profile.store
        store_items = store.get_store_products()
        store_menu = store.menus()
        store_menu_with_items = [
            StoreItmMenuType(menu=menu, items=store_items.filter(product_menu=menu))
            for menu in store_menu
        ]
        return store_menu_with_items

    def resolve_store_items_categories(self, info, store_nickname):
        store_qs = Store.objects.filter(store_nickname=store_nickname)
        if not store_qs.exists():
            raise GraphQLError(
                "Store was not found to get top 10 items, please contact support"
            )
        store = store_qs.first()

        store_items = store.get_store_products()

        store_items_categories = []
        images_used_in_categories = set()
        unique_categories = set()

        for item in store_items:
            item_images = item.product_images.all()
            for category in item.product_categories.all():
                item_image = next(
                    (
                        image.item_image.url
                        for image in item_images
                        if image.item_image.url not in images_used_in_categories
                    ),
                    None,
                )
                if item_image:
                    images_used_in_categories.add(item_image)
                    category_instance: ItemAttribute = category
                    category_data = {
                        "name": category_instance.name,
                        "slug": category_instance.slug,
                        "img": info.context.build_absolute_uri(item_image),
                    }
                    category_key = (category_instance.name, category_instance.slug)
                    if category_key not in unique_categories:
                        unique_categories.add(category_key)
                        store_items_categories.append(category_data)

        return store_items_categories

    def resolve_top10_store_items(self, info, store_nickname):
        store_qs = Store.objects.filter(store_nickname=store_nickname)
        if not store_qs.exists():
            raise GraphQLError(
                "Store was not found to get top 10 items, please contact support"
            )
        store = store_qs.first()
        store_items = (
            store.get_store_products()
            .exclude(
                product_menu__type__slug__icontains="package",
            )
            .exclude(
                product_menu__type__slug__icontains="water",
            )
        )

        return store_items.order_by("-product_views")[:10]

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

        if store:
            store.store_rank += 0.5
            store.save()
        return store
