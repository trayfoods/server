# In your Django app views.py
import json
import hmac
import hashlib
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

SECRET_KEY = settings.PAYSTACK_SECRET_KEY


@csrf_exempt
def paystack_webhook_handler(request):
    if request.method == "POST" and "HTTP_X_PAYSTACK_SIGNATURE_HEADER" in request.META:
        # Get the Paystack signature from the headers
        paystack_signature = request.META["HTTP_X_PAYSTACK_SIGNATURE_HEADER"]
        print(paystack_signature)
        # Get the request body as bytes
        raw_body = request.body

        # Calculate the HMAC using the secret key
        calculated_signature = hmac.new(
            SECRET_KEY.encode("utf-8"), raw_body, hashlib.sha512
        ).hexdigest()

        # Compare the calculated signature with the provided signature
        if hmac.compare_digest(calculated_signature, paystack_signature):
            # Signature is valid, proceed with processing the event
            try:
                event = raw_body.decode("utf-8")
                # Do something with the event here
                # e.g., process_payment(event)
                print(event)
            except UnicodeDecodeError:
                return HttpResponse("Invalid request body encoding", status=400)

            return HttpResponse("Success", status=200)

    return HttpResponse("Invalid request", status=400)
