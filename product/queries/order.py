import graphene
from graphql import GraphQLError
from product.models import Order
from trayapp.permissions import IsAuthenticated, permission_checker
from graphene_django.filter import DjangoFilterConnectionField
from ..types import OrderNode, OrderType, DiscoverDeliveryType

from trayapp.utils import chunked_queryset
import django.db

class OrderQueries(graphene.ObjectType):
    orders = DjangoFilterConnectionField(OrderNode)
    store_orders = DjangoFilterConnectionField(OrderNode)

    deliveries = DjangoFilterConnectionField(OrderNode)
    discover_deliveries = graphene.List(DiscoverDeliveryType)
    get_order = graphene.Field(OrderType, order_id=graphene.String(required=True))

    @permission_checker([IsAuthenticated])
    def resolve_get_order(self, info, order_id):
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

            is_delivery_person = order_qs.linked_delivery_people.filter(
                profile=current_user_profile
            ).exists()
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
    def resolve_discover_deliveries(self, info, **kwargs):
        user = info.context.user
        available_deliveries = []
        if "DELIVERY_PERSON" in user.roles:
            for chunk in chunked_queryset(
                Order.objects.filter(order_status="processing"), chunk_size=100
            ):
                django.db.reset_queries()
                for order in chunk.iterator():
                    if len(order.delivery_people) < 1:
                        # check if delivery person can deliver order
                        if user.profile.delivery_person.can_deliver(order):
                            available_deliveries.append(order)
            return available_deliveries
            # order for order in new_orders if DeliveryPerson.can_deliver(order)
        else:
            raise GraphQLError("You are not a delivery person")

    @permission_checker([IsAuthenticated])
    def resolve_store_orders(self, info, **kwargs):
        user = info.context.user
        if "VENDOR" in user.roles:
            return user.profile.store.orders.all()

    @permission_checker([IsAuthenticated])
    def resolve_deliveries(self, info, **kwargs):
        user = info.context.user
        if "DELIVERY_PERSON" in user.roles:
            return user.profile.delivery_person.orders.all()
        else:
            raise GraphQLError("You are not a delivery person")
