from datetime import timedelta
from pathlib import Path
import os
import json
from dotenv import load_dotenv

# import django secret key generator
from django.core.management.utils import get_random_secret_key

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

import sentry_sdk
import ssl


# FIREBASE SETTINGS
from firebase_admin import initialize_app, credentials
from cryptography.fernet import Fernet

FIREBASE_CONFIG_KEY = os.environ.get("FIREBASE_CONFIG_KEY")
if not "=" in FIREBASE_CONFIG_KEY:
    FIREBASE_CONFIG_KEY = f"{FIREBASE_CONFIG_KEY}="
fernet = Fernet(FIREBASE_CONFIG_KEY)

with open(BASE_DIR / "configs/firebaseServiceAccountKey.bin", "rb") as f:
    firebaseServiceAccountKey_encrypted_data = f.read()
try:
    firebaseServiceAccountKey_data = fernet.decrypt(
        firebaseServiceAccountKey_encrypted_data
    )
except Exception as e:
    # Handle decryption error
    raise ValueError("Decryption failed", e)

cred = credentials.Certificate(json.loads(firebaseServiceAccountKey_data.decode()))
initialize_app(cred)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", str(get_random_secret_key()))
APP_VERSION = os.getenv("APP_VERSION")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = "True" == os.environ.get("DEBUG", "True")

if not DEBUG:
    sentry_sdk.init(
        dsn="https://5d2f9bd6b5edff68cfe4d9d412b6e507@o4506274783756288.ingest.sentry.io/4506274786443279",
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )

USE_S3 = "True" == os.environ.get("USE_S3", "False")
USE_DB = "True" == os.environ.get("USE_DB", "False")

PAYSTACK_SECRET_KEY = os.environ.get(
    "PAYSTACK_SECRET_KEY", "sk_test_a6bda9447b792ea9cdd71c8c656b879e7ae2f407"
)
PAYSTACK_PUBLIC_KEY = os.environ.get(
    "PAYSTACK_PUBLIC_KEY", "pk_test_6babc1ce63e8962d226e26a591af69d2f2067893"
)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "test")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "test")
TWILIO_VERIFY_SERVICE_SID = os.environ.get("TWILIO_VERIFY_SERVICE_SID", "test")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "test")

TERMII_API_KEY = os.environ.get("TERMII_API_KEY", "test")

X_CSCAPI_KEY = os.environ.get("X_CSCAPI_KEY", "1234")


VALID_DELIVERY_TYPES = [
    {
        "name": "pickup",
        "fee": 100,
    },
    {
        "name": "hostel",
        "fee": 400,
    },
]


FRONTEND_URL = os.environ.get("REACT_SITE_DOMAIN", "localhost:3000")

if "localhost:3000" == FRONTEND_URL:
    FRONTEND_URL = "http://%s" % FRONTEND_URL
else:
    FRONTEND_URL = "https://%s" % FRONTEND_URL

ALLOWED_HOSTS = ["api.trayfoods.com", "localhost", "trayfoods.azurewebsites.net"]
SMS_ENABLED = "True" == os.environ.get("SMS_ENABLED", "False")

DATA_UPLOAD_MAX_NUMBER_FIELDS = os.environ.get("DATA_UPLOAD_MAX_NUMBER_FIELDS", 2000)
CSRF_COOKIE_SECURE = DEBUG == False
SESSION_COOKIE_SECURE = DEBUG == False
SECURE_SSL_REDIRECT = DEBUG == False
SECURE_HSTS_SECONDS = 31536000 if (DEBUG == False) else None
SECURE_HSTS_INCLUDE_SUBDOMAINS = DEBUG == False
SECURE_HSTS_PRELOAD = DEBUG == False
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if (DEBUG == False) else None
)
SECURE_BROWSER_XSS_FILTER = DEBUG == False
SECURE_CONTENT_TYPE_NOSNIFF = DEBUG == False

CONN_MAX_AGE = 8600
FILE_UPLOAD_MAX_MEMORY_SIZE = 10_000_000

# Application definition

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "channels",
    "users",
    "product",
    "core",
    "worker",
    "storages",
    "graphene_django",
    "graphql_auth",
    "graphql_jwt.refresh_token.apps.RefreshTokenConfig",
    "django_filters",
    "django_cleanup.apps.CleanupConfig",
    "django_unused_media",
    "anymail",
    "theme",
    "django_countries",
]

USE_MAILERSEND = "True" == os.environ.get("USE_MAILERSEND", "False")

EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
DEFAULT_FROM_EMAIL = "TrayFoods Accounts <{}>".format(EMAIL_HOST_USER)

# MailerSend settings
if USE_MAILERSEND:
    MAILERSEND_API_TOKEN = os.environ.get("MAILERSEND_API_TOKEN")
    EMAIL_BACKEND = "anymail.backends.mailersend.EmailBackend"
    ANYMAIL = {
        "MAILERSEND_API_TOKEN": os.environ.get("MAILERSEND_API_TOKEN"),
    }
    EMAIL_PORT = 465
else:
    # EMAIL_INFOS
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
    EMAIL_PORT = 587

AUTH_USER_MODEL = "users.UserAccount"

GRAPH_MODELS = {
    "all_applications": True,
    "group_models": True,
    "app_labels": ["users", "product"],
}

GRAPHENE = {
    "SCHEMA_CACHE_TIMEOUT": 3600,  # Cache timeout for the GraphQL schema in seconds
    "SCHEMA": "trayapp.schema.schema",
    "MIDDLEWARE": [
        "graphql_jwt.middleware.JSONWebTokenMiddleware",
    ],
}

AUTHENTICATION_BACKENDS = [
    "graphql_jwt.backends.JSONWebTokenBackend",
    "django.contrib.auth.backends.ModelBackend",
]

GRAPHQL_JWT = {
    "JWT_COOKIE_SECURE": True,
    "JWT_HIDE_TOKEN_FIELDS": True,
    "JWT_VERIFY_EXPIRATION": True,
    "JWT_REUSE_REFRESH_TOKENS": True,
    "JWT_LONG_RUNNING_REFRESH_TOKEN": True,
    "JWT_EXPIRATION_DELTA": timedelta(days=7),
    "JWT_AUTH_HEADER_NAME": "HTTP_X_AUTHORIZATION",
    "JWT_ALLOW_ANY_CLASSES": [
        "graphql_auth.mutations.Register",
        "graphql_auth.mutations.VerifyAccount",
        "graphql_auth.mutations.ResendActivationEmail",
        "graphql_auth.mutations.SendPasswordResetEmail",
        "graphql_auth.mutations.PasswordReset",
        "graphql_auth.mutations.ObtainJSONWebToken",
        "graphql_auth.mutations.VerifyToken",
        "graphql_auth.mutations.RefreshToken",
        "graphql_auth.mutations.RevokeToken",
    ],
}

GRAPHQL_AUTH = {
    "EMAIL_FROM": DEFAULT_FROM_EMAIL,
    "EMAIL_TEMPLATE_VARIABLES": {"frontend_domain": FRONTEND_URL},
    "SEND_ACTIVATION_EMAIL": DEBUG == False,
    "ACTIVATION_PATH_ON_EMAIL": "auth/email-activate",
    "SEND_PASSWORD_RESET_EMAIL": DEBUG == False,
    "PASSWORD_RESET_PATH_ON_EMAIL": "auth/password/reset",
    "PASSWORD_SET_PATH_ON_EMAIL": "auth/password/set",
    "REGISTER_MUTATION_FIELDS": ["email", "username", "first_name", "last_name"],
    "UPDATE_MUTATION_FIELDS": ["first_name", "last_name", "email"],
    "USER_NODE_EXCLUDE_FIELDS": ["password", "is_superuser"],
}
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.http.ConditionalGetMiddleware",
]

ROOT_URLCONF = "trayapp.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# WSGI_APPLICATION = "trayapp.wsgi.application"
ASGI_APPLICATION = "trayapp.asgi.application"


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases


if USE_DB:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST"),
            "PORT": os.getenv("DB_PORT"),
            "OPTIONS": {"sslmode": "require"},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "trayfoods",
            "USER": "postgres",
            "PASSWORD": "1234",
            "HOST": "localhost",
            "PORT": "5432",
        },
    }

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


AZURE_ACCOUNT_NAME = os.getenv("AZURE_ACCOUNT_NAME")
if USE_S3:
    # Static files (CSS, JavaScript, Images)
    AZURE_ACCOUNT_KEY = os.getenv("AZURE_ACCOUNT_KEY")

    CUSTOM_DOMAIN = "cdn4trayfoods.blob.core.windows.net"

    # s3 static settings
    STATIC_LOCATION = "static"
    STATIC_URL = f"https://{CUSTOM_DOMAIN}/{STATIC_LOCATION}/"
    STATICFILES_STORAGE = "trayapp.storage_backends.AzureStaticStorage"

    # s3 public media settings
    PUBLIC_MEDIA_LOCATION = "media"
    MEDIA_URL = f"https://ik.imagekit.io/trayfoods/"
    # MEDIA_URL = f"https://{CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"
    DEFAULT_FILE_STORAGE = "trayapp.storage_backends.AzureMediaStorage"

elif not USE_S3:
    STATIC_URL = "/assets/"
    MEDIA_URL = "/media/"
    STATIC_ROOT = BASE_DIR / "workspace/static-root"
    MEDIA_ROOT = BASE_DIR / "workspace/media-root"

STATICFILES_DIRS = [BASE_DIR / "workspace/static"]

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_LOG_SHOW_URLS = True

if DEBUG == False:
    CSRF_TRUSTED_ORIGINS = [
        "https://www.trayfoods.com",
        "https://trayfoods.com",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]


CORS_ORIGIN_WHITELIST = (
    "http://localhost:3000",
    "http://localhost:45678",
    "https://localhost",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "https://www.trayfoods.com",
)

CORS_ALLOW_METHODS = (
    "GET",
    "POST",
    "OPTIONS",
)

CORS_ALLOW_HEADERS = (
    "x-authorization",
    "content-type",
    "origin",
    "x-csrftoken",
    "x-requested-with",
    "accept",
    "accept-encoding",
    "authorization",
    "dnt",
    "user-agent",
    "x-client-data",
    "x-requested-with",
)

# Global settings
DAYS_OF_WEEK = (
    ("Mon", "Mon"),
    ("Tue", "Tue"),
    ("Wed", "Wed"),
    ("Thu", "Thu"),
    ("Fri", "Fri"),
    ("Sat", "Sat"),
    ("Sun", "Sun"),
)
ALLOWED_STORE_ORDER_STATUS = [
    "pending",
    "accepted",
    "rejected",
    "ready-for-pickup",  # also know as "Awaiting Pickup"
    "ready-for-delivery",
    "out-for-delivery",  # also know as "Assigned to Delivery Person & In Transit"
    "picked-up",
    "delivered",
    "no-delivery-person",
    "cancelled",
    "pending-refund",
    "failed-refund",
    "refunded",
    "failed",
]

ALLOWED_DELIVERY_PERSON_ORDER_STATUS = [
    "out-for-delivery",
    "pending",
    "delivered",
    "returned",
    "cancelled",
]
