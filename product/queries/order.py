import graphene
from graphql import GraphQLError
from product.models import Order
from trayapp.permissions import IsAuthenticated, permission_checker
from graphene_django.filter import DjangoFilterConnectionField
from ..types import OrderNode, OrderType


class OrderQueries(graphene.ObjectType):
    orders = DjangoFilterConnectionField(OrderNode)
    store_orders = DjangoFilterConnectionField(OrderNode)

    deliveries = DjangoFilterConnectionField(OrderNode)
    get_order = graphene.Field(OrderType, order_id=graphene.String(required=True))

    @permission_checker([IsAuthenticated])
    def resolve_get_order(self, info, order_id):
        user = info.context.user
        allowed_view_as_roles = ["DELIVERY_PERSON", "VENDOR"]

        order = user.orders.filter(order_track_id=order_id).first()

        if user.role in allowed_view_as_roles:
            current_user_profile = user.profile
            order_qs = Order.objects.filter(order_track_id=order_id).first()
            if order_qs is None:
                raise GraphQLError("Order Not Found")

            is_delivery_person = (
                order_qs.delivery_person
                and order_qs.delivery_person.profile == current_user_profile
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
    def resolve_orders(self, info):
        return info.context.user.orders.all()

    @permission_checker([IsAuthenticated])
    def resolve_store_orders(self, info):
        user = info.context.user
        if user.role == "VENDOR":
            return user.profile.store.orders.all()

    @permission_checker([IsAuthenticated])
    def resolve_deliveries(self, info):
        user = info.context.user
        if user.role == "DELIVERY_PERSON":
            return user.profile.delivery_person.orders.all()
        else:
            raise GraphQLError("You are not a delivery person")
