import os
from dotenv import load_dotenv

load_dotenv()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from trayapp.middlewares import JwtTokenAuthMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trayapp.settings')
# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

import trayapp.routing


application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
            JwtTokenAuthMiddleware(URLRouter(trayapp.routing.websocket_urlpatterns))
        )
})