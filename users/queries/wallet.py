import graphene
from trayapp.permissions import IsAuthenticated, permission_checker
from users.models import Wallet
from users.types import WalletInfoNode


class WalletQueries(graphene.ObjectType):
    wallet_info = graphene.Field(WalletInfoNode)

    @permission_checker([IsAuthenticated])
    def resolve_wallet_info(self, info, **kwargs):
        wallet = Wallet.objects.filter(user=info.context.user.profile).first()
        if wallet:
            return WalletInfoNode(
                balance=wallet.balance,
                success=True,
            )
        return WalletInfoNode(success=False)
