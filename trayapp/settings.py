from datetime import timedelta
from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = "True" in os.getenv("DEBUG")
USE_S3 = "True" in os.getenv("USE_S3")
USE_DB = "True" in os.getenv("USE_DB")

# EMAIL_INFOS
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_USE_TLS = True
EMAIL_PORT = 587
DEFAULT_FROM_EMAIL = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

if DEBUG == True:
    FRONTEND_URL = "http://localhost:3000"
else:
    FRONTEND_URL = "https://%s" % os.getenv("REACT_SITE")

ALLOWED_HOSTS = [
    "127.0.0.1",
    "192.168.137.1",
    "localhost",
    "%s" % os.getenv("SITE_ORIGIN_URL"),
]

CSRF_COOKIE_SECURE = DEBUG == False
SESSION_COOKIE_SECURE = DEBUG == False
SECURE_SSL_REDIRECT = DEBUG == False
SECURE_HSTS_SECONDS = 518400 if (DEBUG == False) else None
SECURE_HSTS_INCLUDE_SUBDOMAINS = DEBUG == False
SECURE_HSTS_PRELOAD = DEBUG == False
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if (DEBUG == False) else None
)

CONN_MAX_AGE = 8600
FILE_UPLOAD_MAX_MEMORY_SIZE = 10000000

# Application definition

INSTALLED_APPS = [
    # "django.contrib.gis",
    # "daphne",
    "channels",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",  # Required for GraphiQL
    "users",
    "product",
    "graphene_django",
    "graphql_auth",
    "django_filters",
    "django_cleanup.apps.CleanupConfig",
    "django_unused_media",
    "graphql_jwt.refresh_token.apps.RefreshTokenConfig",
    "corsheaders",
    "django_extensions",
    "rest_framework",
]

AUTH_USER_MODEL = "users.UserAccount"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        'ROUTING': 'trayapp.routing.websocket_urlpatterns',
        "CONFIG": {
            "hosts": [("localhost", 6379)],
        },
    },
}

GRAPH_MODELS = {
    "all_applications": True,
    "group_models": True,
    "app_labels": ["users", "product"],
}

GRAPHENE = {
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
    "JWT_ALLOW_ARGUMENT": True,
    "JWT_VERIFY_EXPIRATION": True,
    "JWT_LONG_RUNNING_REFRESH_TOKEN": True,
    "JWT_REFRESH_TOKEN_EXPIRATION_DELTA": timedelta(days=7),
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
    "SEND_PASSWORD_RESET_EMAIL": True,
    "PASSWORD_RESET_PATH_ON_EMAIL": "auth/password-reset",
    "PASSWORD_SET_PATH_ON_EMAIL": "auth/password-set",
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

WSGI_APPLICATION = "trayapp.wsgi.application"
ASGI_APPLICATION = "trayapp.asgi.application"


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
if USE_DB == True:
    db_from_env = dj_database_url.config(conn_max_age=600)
    DATABASES["default"].update(db_from_env)

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


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

if USE_S3:
    # aws settings
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_DEFAULT_ACL = os.getenv("AWS_DEFAULT_ACL")
    if AWS_DEFAULT_ACL == "None":
        AWS_DEFAULT_ACL = None
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.eu-west-2.amazonaws.com"
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    AWS_S3_SECURE_URLS = True

    # s3 static settings
    STATIC_LOCATION = "static"
    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{STATIC_LOCATION}/"
    STATICFILES_STORAGE = "trayapp.storage_backends.StaticStorage"

    # s3 cached static settings
    COMPRESS_URL = STATIC_URL
    COMPRESS_ROOT = BASE_DIR / "staticfiles"
    COMPRESS_STORAGE = "trayapp.storage_backends.CachedStaticS3BotoStorage"

    # s3 public media settings
    PUBLIC_MEDIA_LOCATION = "media"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"
    DEFAULT_FILE_STORAGE = "trayapp.storage_backends.PublicMediaStorage"

    # s3 private media settings
    PRIVATE_MEDIA_LOCATION = "private"
    PRIVATE_FILE_STORAGE = "trayapp.storage_backends.PrivateMediaStorage"

elif not USE_S3:
    STATIC_URL = "/assets/"
    MEDIA_URL = "/media/"
    STATIC_ROOT = BASE_DIR / "workspace/static-root"
    MEDIA_ROOT = BASE_DIR / "workspace/media-root"

STATICFILES_DIRS = [BASE_DIR / "workspace/static"]

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if DEBUG == True:
    CORS_ORIGIN_ALLOW_ALL = True
else:
    CORS_ORIGIN_WHITELIST = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.137.1:3000",
        FRONTEND_URL,
    )

CORS_ALLOW_METHODS = (
    "GET",
    "POST",
    "OPTIONS",
)

CORS_ALLOW_HEADERS = (
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
)
