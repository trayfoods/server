import graphene
from graphql import GraphQLError
from product.models import Order
from users.models import DeliveryPerson, Profile
from trayapp.permissions import IsAuthenticated, permission_checker
from graphene_django.filter import DjangoFilterConnectionField
from ..types import (
    OrderNode,
    StoreOrderNode,
    DeliveryPersonOrderNode,
    OrderType,
    StatusOrdersCountType,
)

from django.utils import timezone


class OrderQueries(graphene.ObjectType):
    orders = DjangoFilterConnectionField(OrderNode)
    store_orders = DjangoFilterConnectionField(StoreOrderNode)

    deliveries = DjangoFilterConnectionField(DeliveryPersonOrderNode)
    get_order = graphene.Field(OrderType, order_id=graphene.String(required=True))

    order_status = graphene.String(order_id=graphene.String(required=True))

    status_orders_count = graphene.List(
        StatusOrdersCountType,
        statuses=graphene.List(graphene.String),
        who=graphene.String(),
    )

    @permission_checker([IsAuthenticated])
    def resolve_get_order(self, info, order_id):
        order_id = order_id.lower()
        user = info.context.user
        allowed_view_as_roles = ["DELIVERY_PERSON", "VENDOR"]

        order = user.orders.filter(order_track_id=order_id).first()

        # check if allowed_view_as_roles is in user.roles
        is_allowed_view_as_roles = any(
            role in user.roles for role in allowed_view_as_roles
        )

        if is_allowed_view_as_roles:
            current_user_profile = user.profile
            order_qs = Order.objects.filter(order_track_id=order_id).first()
            if order_qs is None:
                raise GraphQLError("Order Not Found")

            delivery_person: DeliveryPerson = user.profile.get_delivery_person()
            is_delivery_person = False
            if delivery_person:
                is_delivery_person = order_qs.linked_delivery_people.filter(
                    profile=current_user_profile
                ).exists() or (
                    delivery_person.get_notifications()
                    .filter(order=order_qs, delivery_person__id=delivery_person.id)
                    .exists()
                )
            is_vendor = order_qs.linked_stores.filter(
                vendor=current_user_profile
            ).exists()

            if is_delivery_person or is_vendor:
                return order_qs

        if order:
            return order
        else:
            raise GraphQLError("Order Not Found")

    @permission_checker([IsAuthenticated])
    def resolve_orders(self, info, **kwargs):
        return info.context.user.orders.all()

    @permission_checker([IsAuthenticated])
    def resolve_store_orders(self, info, **kwargs):
        user = info.context.user
        if "VENDOR" in user.roles:
            return user.profile.store.orders.all()
        else:
            raise GraphQLError("You are not a vendor")

    @permission_checker([IsAuthenticated])
    def resolve_deliveries(self, info, **kwargs):
        user = info.context.user
        profile: Profile = user.profile
        if "DELIVERY_PERSON" in user.roles:
            return profile.get_delivery_person().orders.all()
        else:
            raise GraphQLError("You are not a delivery person")

    @permission_checker([IsAuthenticated])
    def resolve_order_status(self, info, order_id):
        user = info.context.user
        current_user_profile = user.profile
        order_qs = Order.objects.filter(order_track_id=order_id)
        if not order_qs.exists():
            raise GraphQLError("Order Not Found")

        return order_qs.first().get_order_status(current_user_profile)

    @permission_checker([IsAuthenticated])
    def resolve_status_orders_count(self, info, statuses: list[str], who: str):
        statuses_with_counts = []
        user = info.context.user
        profile: Profile = user.profile
        who = who.lower()
        if not who in ["delivery_person", "vendor"]:
            raise GraphQLError("Invalid Role")

        orders = []

        if who == "vendor":
            if not "VENDOR" in user.roles:
                raise GraphQLError("You are not a vendor")
            # get recent orders
            orders: list[Order] = profile.store.orders
            # .filter(
            #     created_at__date__gte=timezone.now().date()
            #     - timezone.timedelta(days=7)  # get orders from the last 7 days
            # )
        elif who == "delivery_person":
            if not "DELIVERY_PERSON" in user.roles:
                raise GraphQLError("You are not a delivery person")
            orders: list[Order] = profile.get_delivery_person().orders.all()

        else:
            raise GraphQLError("Invalid Role")

        orders_not_seen_by_profile = orders.exclude(
            profiles_seen__contains=[profile.id]
        )
        for status in statuses:
            status = status.upper()
            orders_with_status_new_count = [
                order
                for order in orders_not_seen_by_profile
                if order.get_order_status(profile).upper() in status
                and not profile.id in order.profiles_seen
            ]
            orders_with_status_count = [
                order
                for order in orders
                if order.get_order_status(profile).upper() in status
            ]

            if status == "ONGOING":
                # get orders with status ["pening", "out-for-delivery"]
                orders_with_status_count = [
                    order
                    for order in orders
                    if order.get_order_status(profile).upper().replace("_", "-")
                    in ["PENDING", "OUT-FOR-DELIVERY"]
                ]

            elif status == "READY":
                # get orders with status ["ready-for-pickup", "ready-for-delivery", "no-delivery-person"]
                orders_with_status_count = [
                    order
                    for order in orders
                    if order.get_order_status(profile).upper()
                    in ["READY_FOR_PICKUP", "READY_FOR_DELIVERY", "NO_DELIVERY_PERSON"]
                ]

            elif status == "COMPLETED":
                # get orders with status ["delivered", "picked-up"]
                orders_with_status_count = [
                    order
                    for order in orders
                    if order.get_order_status(profile).upper()
                    in ["DELIVERED", "PICKED_UP"]
                ]

            statuses_with_counts.append(
                {
                    "status": status,
                    "count": len(orders_with_status_count),
                    "new_count": len(orders_with_status_new_count),
                }
            )
        return statuses_with_counts
