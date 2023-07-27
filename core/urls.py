from django.urls import path
from core.views import paystack_webhook_handler

urlpatterns = [
    path("paystack-webhook", paystack_webhook_handler, name="paystack-webhook"),
]