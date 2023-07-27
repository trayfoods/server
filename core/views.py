from django.http import JsonResponse


def order_payment_webhook(request):
    if request.method == "POST":
        body = request.body
        print("", body)
        return JsonResponse({"status": "success"})
    else:
        return JsonResponse({"status": "failed"})
