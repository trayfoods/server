import graphene
from trayapp.permissions import IsAuthenticated, permission_checker
from users.models import Profile
from ..types import WalletNode


class WalletQueries(graphene.ObjectType):
    wallet = graphene.Field(WalletNode)

    @permission_checker([IsAuthenticated])
    def resolve_wallet(self, info, **kwargs):
        user_profile: Profile = info.context.user.profile
        wallet = user_profile.get_wallet()
        if not wallet:
            return WalletNode(success=False, error="Wallet not found")
        
        return WalletNode(
            balance=wallet.balance,
            unsettled_balance=wallet.get_unsettled_balance(),
            success=True,
        )
