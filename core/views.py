# In your Django app views.py
import json
import hmac
import hashlib
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.encoding import force_bytes
from django.conf import settings

from .utils import ProcessPayment

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY

PAYSTACK_WHITELISTED_IPS = [
    "52.31.139.75",
    "52.49.173.169",
    "52.214.14.220",
]

if settings.DEBUG:
    PAYSTACK_WHITELISTED_IPS += ["127.0.0.1", "localhost"]


@csrf_exempt
def paystack_webhook_handler(request):
    HTTP_X_PAYSTACK_SIGNATURE_EXIST = (
        "HTTP_X_PAYSTACK_SIGNATURE" in request.META
        or "HTTP_X_PAYSTACK_SIGNATURE_HEADER" in request.META
    )

    # check if the request is from paystack
    if request.META["REMOTE_ADDR"] not in PAYSTACK_WHITELISTED_IPS:
        return HttpResponse("Invalid IP", status=403)

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
