# In your Django app views.py
import json
import hmac
import hashlib
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.utils.encoding import force_bytes
from django.conf import settings

from product.models import Order

from .utils import ProcessPayment

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY


@csrf_exempt
def paystack_webhook_handler(request):
    HTTP_X_PAYSTACK_SIGNATURE_EXIST = (
        "HTTP_X_PAYSTACK_SIGNATURE" in request.META
        or "HTTP_X_PAYSTACK_SIGNATURE_HEADER" in request.META
    )

    # update HTTP_X_PAYSTACK_SIGNATURE_HEADER in request.META
    if "HTTP_X_PAYSTACK_SIGNATURE_HEADER" in request.META:
        request.META["HTTP_X_PAYSTACK_SIGNATURE"] = request.META[
            "HTTP_X_PAYSTACK_SIGNATURE_HEADER"
        ]

    if request.method == "POST" and HTTP_X_PAYSTACK_SIGNATURE_EXIST:
        # Get the Paystack signature from the headers
        paystack_signature = request.META["HTTP_X_PAYSTACK_SIGNATURE"]
        # Get the request body as bytes
        raw_body = request.body
        decoded_body = raw_body.decode("utf-8")

        # Calculate the HMAC using the secret key
        calculated_signature = hmac.new(
            key=force_bytes(PAYSTACK_SECRET_KEY),
            msg=force_bytes(decoded_body),
            digestmod=hashlib.sha512,
        ).hexdigest()

        # Compare the calculated signature with the provided signature
        if hmac.compare_digest(calculated_signature, paystack_signature):
            # Signature is valid, proceed with processing the event
            try:
                # get the event from request.body
                event = json.loads(raw_body)
                # get the event type from event
                event_type = event["event"]
                # get the event data from event
                event_data = event["data"]
                # process_payment
                process_payment = ProcessPayment(event_type, event_data)
                return process_payment.process_payment()

                # return JsonResponse(
                #     {
                #         "status": event["event"],
                #     },
                #     status=200,
                # )
            except UnicodeDecodeError:
                return HttpResponse("Invalid request body encoding", status=400)

        else:
            return HttpResponse("NOT ALLOWED", status=403)

    return HttpResponse("Invalid request", status=400)


def order_redirect_share_view(request, order_id):
    order = Order.objects.filter(order_track_id=order_id).first()
    if order:
        if not order.order_payment_url:
            order.create_payment_link
            order = Order.objects.filter(order_track_id=order.order_track_id).first()
        return redirect(order.order_payment_url)
    return JsonResponse(
        {"message": "Order not found, you were shared the wrong order payment link"},
        status=404,
    )
