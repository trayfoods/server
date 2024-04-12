from django.urls import path
from . import views

urlpatterns = [
    path("order/process-delivery-notification/", views.process_delivery_notification, name="process-delivery-notification"),
    path("order/process-delivery-notification-sent/", views.process_delivery_notification_sent, name="process-delivery-notification-sent"),
]
