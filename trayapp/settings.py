from datetime import timedelta
from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-#)2!^38c7a772a9b3716")
APP_VERSION = os.getenv("APP_VERSION")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = "True" in os.environ.get("DEBUG", "True")

USE_S3 = "True" in os.environ.get("USE_S3", "False")
USE_DB = "True" in os.environ.get("USE_DB", "False")

PAYSTACK_SECRET_KEY = os.environ.get(
    "PAYSTACK_SECRET_KEY", "sk_test_5ade8b7c938c7a772a9b3716edc14d3ba8ce61ff"
)
PAYSTACK_PUBLIC_KEY = os.environ.get(
    "PAYSTACK_PUBLIC_KEY", "pk_test_6babc1ce63e8962d226e26a591af69d2f2067893"
)

USE_SES = "True" in os.environ.get("USE_SES", "False")

EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.getenv("EMAIL_HOST_USER")

# Amazon SES settings
if USE_SES:
    EMAIL_BACKEND = "anymail.backends.amazon_ses.EmailBackend"
    # EMAIL_BACKEND = "django_ses.SESBackend"
    EMAIL_PORT = 465
    AWS_SES_REGION_NAME = os.getenv("AWS_DEFAULT_REGION")
    AWS_SES_REGION_ENDPOINT = "email.{}.amazonaws.com".format(AWS_SES_REGION_NAME)
else:
    # EMAIL_INFOS
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
    EMAIL_PORT = 587

FRONTEND_URL = os.environ.get("REACT_SITE", "http://localhost:3000")

if "localhost" in FRONTEND_URL:
    FRONTEND_URL = "http://%s" % os.getenv("REACT_SITE")

if DEBUG == True:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [
        "127.0.0.1",
        "192.168.137.1",
        "localhost",
        "%s" % os.environ.get("SITE_ORIGIN_URL", "api.trayfoods.com"),
    ]
DATA_UPLOAD_MAX_NUMBER_FIELDS = os.environ.get("DATA_UPLOAD_MAX_NUMBER_FIELDS", 2000)
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
FILE_UPLOAD_MAX_MEMORY_SIZE = 10_000_000

# Application definition

INSTALLED_APPS = [
    # "django.contrib.gis",
    "daphne",
    # "channels",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",  # Required for GraphiQL
    "users",
    "product",
    "core",
    "storages",
    "graphene_django",
    "graphql_auth",
    "django_filters",
    "django_cleanup.apps.CleanupConfig",
    "django_unused_media",
    "graphql_jwt.refresh_token.apps.RefreshTokenConfig",
    "corsheaders",
    "django_extensions",
    "rest_framework",
    "anymail",
]

AUTH_USER_MODEL = "users.UserAccount"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get("REDIS_URL", "redis://127.0.0.1:6379")],
        },
    },
}
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://127.0.0.1:6379"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

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
    "JWT_ALLOW_ARGUMENT": True,
    "JWT_LONG_RUNNING_REFRESH_TOKEN": True,
    "JWT_EXPIRATION_DELTA": timedelta(days=7),
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

WSGI_APPLICATION = "trayapp.wsgi.application"
ASGI_APPLICATION = "trayapp.asgi.application"


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

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


# Amazon S3 settings
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")

if USE_S3:
    # Static files (CSS, JavaScript, Images)
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_DEFAULT_ACL = os.getenv("AWS_DEFAULT_ACL")
    if AWS_DEFAULT_ACL == "None":
        AWS_DEFAULT_ACL = None
    AWS_S3_CUSTOM_DOMAIN = (
        f"{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_DEFAULT_REGION}.amazonaws.com"
    )
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
