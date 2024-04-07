from users.models import DeliveryNotification  # Assuming DeliveryNotification model in your Django project

def get_delivery_notification(order_id, delivery_person_id):
    try:
        return DeliveryNotification.objects.get(order_id=order_id, delivery_person_id=delivery_person_id)
    except DeliveryNotification.DoesNotExist:
        return None

def update_delivery_notification(delivery_notification, status):
    delivery_notification.status = status
    delivery_notification.save()
