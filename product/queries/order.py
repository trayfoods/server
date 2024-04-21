import graphene
from graphql import GraphQLError
from product.models import Order
from users.models import DeliveryNotification
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
    # discover_deliveries = graphene.List(DiscoverDeliveryType)
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

            delivery_person = user.profile.get_delivery_person()
            delivery_person_id = (
                user.profile.get_delivery_person().id if delivery_person else None
            )

            is_delivery_person = order_qs.linked_delivery_people.filter(
                profile=current_user_profile
            ).exists() or (
                delivery_person_id
                and DeliveryNotification.objects.filter(
                    order=order, delivery_person__id=delivery_person_id
                ).exists()
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

    # @permission_checker([IsAuthenticated])
    # def resolve_discover_deliveries(self, info, **kwargs):
    #     user = info.context.user
    #     available_deliveries = []
    #     if "DELIVERY_PERSON" in user.roles:
    #         for chunk in chunked_queryset(
    #             Order.objects.filter(order_status="processing"), chunk_size=100
    #         ):
    #             django.db.reset_queries()
    #             for order in chunk.iterator():
    #                 if len(order.delivery_people) < 1:
    #                     # check if delivery person can deliver order
    #                     if user.profile.get_delivery_person().can_deliver(order):
    #                         available_deliveries.append(order)
    #         return available_deliveries
    #         # order for order in new_orders if DeliveryPerson.can_deliver(order)
    #     else:
    #         raise GraphQLError("You are not a delivery person")

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
        if "DELIVERY_PERSON" in user.roles:
            return user.profile.get_delivery_person().orders.all()
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
        profile = user.profile
        who = who.lower()
        if not who in ["delivery_person", "vendor"]:
            raise GraphQLError("Invalid Role")

        orders = []

        if who == "vendor":
            if not "VENDOR" in user.roles:
                raise GraphQLError("You are not a vendor")
            # get recent orders
            orders: list[Order] = profile.store.orders.filter(
                created_at__date__gte=timezone.now().date()
                - timezone.timedelta(days=7)  # get orders from the last 7 days
            )
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
            orders_with_status = [
                order
                for order in orders_not_seen_by_profile
                if order.get_order_status(profile).upper() == status
                and not profile.id in order.profiles_seen
            ]
            statuses_with_counts.append(
                {"status": status, "count": len(orders_with_status)}
            )
        return statuses_with_counts
