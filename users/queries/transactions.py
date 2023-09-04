import graphene
from graphene_django.filter import DjangoFilterConnectionField
from trayapp.permissions import IsAuthenticated, permission_checker
from users.models import Transaction
from users.types import TransactionNode


class TransactionQueries(graphene.ObjectType):
    transaction = graphene.relay.Node.Field(TransactionNode)
    transactions = DjangoFilterConnectionField(
        TransactionNode
    )

    @permission_checker([IsAuthenticated])
    def resolve_transactions(self, info, **kwargs):
        user = info.context.user
        profile = user.profile
        return Transaction.objects.filter(wallet__user=profile)
