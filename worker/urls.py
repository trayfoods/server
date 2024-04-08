from django.urls import path
from . import views

urlpatterns = [
    path("order/delivery-request/", views.process_delivery_notification, name="process-delivery-notification"),
]
