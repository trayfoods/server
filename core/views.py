# In your Django app views.py
import json
import hmac
import hashlib
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.encoding import force_bytes
from django.conf import settings

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
        event = raw_body.decode("utf-8")

        # Calculate the HMAC using the secret key
        calculated_signature = hmac.new(
            key=force_bytes(PAYSTACK_SECRET_KEY),
            msg=force_bytes(event),
            digestmod=hashlib.sha512,
        ).hexdigest()

        print(event)

        # Compare the calculated signature with the provided signature
        if hmac.compare_digest(calculated_signature, paystack_signature):
            # Signature is valid, proceed with processing the event
            try:
                # Do something with the event here
                # e.g., process_payment(event)
                print(event)
                return JsonResponse(
                    {"status": "success", "data": event},
                    status=200,
                )
            except UnicodeDecodeError:
                return HttpResponse("Invalid request body encoding", status=400)

            #  return HttpResponse("Success", status=200)

    return HttpResponse("Invalid request", status=400)
