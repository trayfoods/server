from django.http import JsonResponse
import requests


def get_bank_list(request) -> JsonResponse:
    if request.user.is_authenticated:
        url = "https://api.paystack.co/bank?country=nigeria&currency=NGN"
        headers = {
            'Authorization': 'Bearer sk_test_6f9d6c2c6b0f6e1c1a8a2a2f0e5d0a5f6c8f1b9a',
            'Content-Type': 'application/json',
        }
        response = requests.request("GET", url, headers=headers)
        return JsonResponse(response.json()['data'], safe=False)
    else:
        return JsonResponse({'error': 'Not logged in'}, safe=False)
