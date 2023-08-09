from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Wallet
from .signals import balance_updated

@receiver(post_save, sender=Wallet, dispatch_uid="wallet_balance_updated")
def wallet_balance_updated(sender, instance, **kwargs):
    if kwargs.get("update_fields") is None or "balance" in kwargs["update_fields"]:
        balance_updated.send(sender=instance.__class__, balance=instance.balance)
