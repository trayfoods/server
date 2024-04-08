from django.shortcuts import render
from django.http import JsonResponse
from users.models import DeliveryPerson, Store
from product.models import Order
from django.views.decorators.csrf import csrf_exempt


# Process delivery request
# then return delivery person device_ids:[], store_name: str and store_id: int
@csrf_exempt
def process_delivery_notification(request):
    if request.method == "POST":
        data = request.POST
        order_id = data.get("order_id")
        delivery_person_id = data.get("delivery_person_id")
        order_qs = Order.objects.filter(id=order_id)
        if not order_qs.exists():
            return JsonResponse({"error": "Order does not exist", "status": False})

        order = order_qs.first()
        delivery_notification = order.get_delivery_notification(
            order_id, delivery_person_id
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
            device_ids = delivery_person.profile.user.devices.all().values_list(
                "device_id", flat=True
            )

            delivery_notification.status = "processing"
            delivery_notification.save()
            return JsonResponse(
                {
                    "success": True,
                    "device_ids": device_ids,
                    "store_name": store_name,
                    "store_id": store_id,
                }
                , safe=False
            )
    return JsonResponse({"error": "Invalid request"})
