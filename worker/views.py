from django.http import JsonResponse
from users.models import DeliveryPerson, Store
from product.models import Order
from django.views.decorators.csrf import csrf_exempt
from trayapp.utils import send_message_to_queue_bus


# Process delivery request
# then return delivery person device_ids:[], store_name: str and store_id: int
@csrf_exempt
def process_delivery_notification(request):
    if request.method == "POST":
        data = request.POST
        order_id = data.get("order_id")
        delivery_person_id = data.get("delivery_person_id")
        order_qs = Order.objects.filter(order_track_id=order_id)
        if not order_qs.exists():
            return JsonResponse({"error": "Order does not exist", "status": False})

        order = order_qs.first()
        try:
            delivery_notification = order.get_delivery_notification(delivery_person_id)
        except:
            delivery_notification = order.get_delivery_notification(
                delivery_person_id[0]
            )

        if delivery_notification:
            store: Store = delivery_notification.store
            store_name = store.store_name
            store_id = store.id
            delivery_person_qs = DeliveryPerson.objects.filter(id=delivery_person_id)
            if not delivery_person_qs.exists():
                return JsonResponse(
                    {"error": "delivery person not found", "success": False}
                )
            delivery_person = delivery_person_qs.first()
            device_tokens = delivery_person.profile.user.devices.all().values_list(
                "device_token", flat=True
            )

            delivery_notification.status = "processing"
            delivery_notification.save()

            data = {
                "success": True,
                "device_tokens": list(device_tokens),
                "store_name": store_name,
                "email": delivery_person.profile.user.email,
                "store_id": store_id,
            }
            return JsonResponse(data=data, safe=False)
    return JsonResponse({"error": "Invalid request"})


@csrf_exempt
def process_delivery_notification_sent(request):
    if request.method == "POST":
        data = request.POST
        order_id = data.get("order_id")
        delivery_person_id = data.get("delivery_person_id")
        order_qs = Order.objects.filter(order_track_id=order_id)
        if not order_qs.exists():
            return JsonResponse({"error": "Order does not exist", "status": False})

        order = order_qs.first()
        try:
            delivery_notification = order.get_delivery_notification(delivery_person_id)
        except:
            delivery_notification = order.get_delivery_notification(
                delivery_person_id[0]
            )

        if delivery_notification:
            delivery_person_qs = DeliveryPerson.objects.filter(id=delivery_person_id)
            if not delivery_person_qs.exists():
                return JsonResponse(
                    {"error": "delivery person not found", "success": False}
                )
            delivery_notification.status = "sent"
            delivery_notification.save()
            message = {
                "order_id": data.get("order_id"),
                "delivery_person_id": data.get("delivery_person_id"),
            }
            # send message to queue bus with 30 seconds ttl in milliseconds
            send_message_to_queue_bus(
                message_dict=message, queue_name="sent-delivery-request", ttl=60
            )

            data = {
                "success": True,
            }
            return JsonResponse(data=data, safe=False)
    return JsonResponse({"error": "Invalid request"})
