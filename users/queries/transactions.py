import graphene
from graphene_django.filter import DjangoFilterConnectionField
from users.models import Transaction
from users.types import TransactionNode


class TransactionQueries(graphene.ObjectType):
    transactions = DjangoFilterConnectionField(TransactionNode)

    def resolve_transactions(self, info, **kwargs):
        return Transaction.objects.all()
