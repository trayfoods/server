from django.urls import path
from core.views import paystack_webhook_handler, order_redirect_share_view

urlpatterns = [
    path("paystack-webhook", paystack_webhook_handler, name="paystack-webhook"),
    path("share-order/<str:order_id>", order_redirect_share_view, name="share-order"),
]
