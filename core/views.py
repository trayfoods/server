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
    if request.method == "POST":
        # Get the request headers and body
        raw_body = request.body
        headers = request.headers

        # Get the Paystack signature from the headers
        paystack_signature = headers.get('HTTP_X_PAYSTACK_SIGNATURE', '')

        # Calculate the HMAC using the secret key
        calculated_signature = hmac.new(
            key=bytes(SECRET_KEY, 'utf-8'),
            msg=raw_body,
            digestmod=hashlib.sha512
        ).hexdigest()

        # Compare the calculated signature with the provided signature
        if hmac.compare_digest(calculated_signature, paystack_signature):
            # Signature is valid, proceed with processing the event
            try:
                event = json.loads(raw_body)
                # Do something with the event here
                # e.g., process_payment(event)
                print(event)
                pass
            except json.JSONDecodeError:
                return HttpResponse("Invalid JSON payload", status=400)

            return HttpResponse("Success", status=200)

    return HttpResponse("Invalid request", status=400)
