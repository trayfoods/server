# In your Django app views.py
import json
import hmac
import hashlib
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

SECRET_KEY = settings.PAYSTACK_SECRET_KEY

@csrf_exempt
def order_payment_webhook(request):
    if request.method == "POST" and 'HTTP_X_PAYSTACK_SIGNATURE' in request.META:
        # Get the Paystack signature from the headers
        paystack_signature = request.META['HTTP_X_PAYSTACK_SIGNATURE']

        # Get the request body as bytes
        raw_body = request.body

        # Calculate the HMAC using the secret key
        calculated_signature = hashlib.sha512(raw_body + SECRET_KEY.encode()).hexdigest()

        # Compare the calculated signature with the provided signature
        if hmac.compare_digest(calculated_signature, paystack_signature):
            # Signature is valid, proceed with processing the event
            try:
                event = raw_body.decode('utf-8')
                # Do something with the event here
                # e.g., process_payment(event)
                print(event)
            except UnicodeDecodeError:
                return HttpResponse("Invalid request body encoding", status=400)

            return HttpResponse("Success", status=200)

    return HttpResponse("Invalid request", status=400)
