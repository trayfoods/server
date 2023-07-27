from django.urls import path
from core.views import order_payment_webhook

urlpatterns = [
    path("order-payment-webhook", order_payment_webhook, name="rest-api"),
]