from django.urls import re_path
from users.consumers import CheckEmailVerificationConsumer

websocket_urlpatterns = [
    re_path(r'check_email_verification/$', CheckEmailVerificationConsumer.as_asgi()),
]
