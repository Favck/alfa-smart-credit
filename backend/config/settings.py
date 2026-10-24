import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "development-only-alfa-potok-change-before-deployment"
)
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,[::1]"
).split(",")
DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"
ML_BASE_URL = os.environ.get("ML_BASE_URL", "http://127.0.0.1:8001")
ML_TIMEOUT_SECONDS = min(
    15, max(0.1, float(os.environ.get("ML_TIMEOUT_SECONDS", "2.5")))
)
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "api",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
(BASE_DIR / "data").mkdir(exist_ok=True)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "data" / "db.sqlite3",
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttrib"
            "uteSimilarityValidator"
        )
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {
        "NAME": (
            "django.contrib.auth.password_validation.CommonPass"
            "wordValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation.NumericPas"
            "swordValidator"
        )
    },
]
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
CSRF_TRUSTED_ORIGINS = [
    origin
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin
]
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    if SECRET_KEY.startswith("development-only"):
        raise ValueError("DJANGO_SECRET_KEY is required in production")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication"
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated"
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "120/minute"},
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Альфа.Поток — Backend API",
    "VERSION": "0.1.0",
    "OAS_VERSION": "3.0.3",
    "DESCRIPTION": """Черновой контракт Django ↔ Vue для хакатона.""",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": False,
        "displayRequestDuration": True,
    },
    "ENUM_NAME_OVERRIDES": {
        "ApplicationStatusEnum": "api.serializers.APPLICATION_STATUSES",
        "ProductCodeEnum": "api.serializers.PRODUCT_CODES",
        "DemoProfileIdEnum": "api.serializers.DEMO_PROFILE_IDS",
    },
    "TAGS": [
        {"name": "Система", "description": "Проверка доступности."},
        {
            "name": "Демо-вход",
            "description": (
                "Выбор готового профиля, " "без регистрации и паролей."
            ),
        },
        {
            "name": "Компания",
            "description": "Профиль компании текущего клиента.",
        },
        {"name": "Продукты", "description": "Каталог кредитных продуктов."},
        {
            "name": "Новости",
            "description": "Локальные статьи с подбором по отрасли компании.",
        },
        {
            "name": "Заявки",
            "description": "Создание, черновики и движение заявки.",
        },
        {
            "name": "Скоринг",
            "description": (
                "Предварительный расчёт и понятное " "объяснение риска."
            ),
        },
        {
            "name": "Документы",
            "description": "Выписки, договор и имитация подписания.",
        },
        {
            "name": "Офферы",
            "description": "Условия банка и ответ клиента.",
        },
        {
            "name": "Банк",
            "description": "Очередь и решения андеррайтера.",
        },
    ],
}
