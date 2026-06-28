from pathlib import Path
from decouple import config, Csv
from django.templatetags.static import static
from django.urls import reverse_lazy

# ── Base ───────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# ── Applications ───────────────────────────────────────
INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',

    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    'django_htmx',
    'axes',
    'channels',

    'notifications',
    'accounts',
    'inventory',
    'procurement',
    'operations',
    'assets',
    'reports',
]

# ── Middleware ─────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'axes.middleware.AxesMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ── Templates ──────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.tutorial_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ── Database ───────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME':     config('DB_NAME',     default='wms_db'),
        'USER':     config('DB_USER',     default='wms_user'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST':     config('DB_HOST',     default='localhost'),
        'PORT':     config('DB_PORT',     default='5432'),
    }
}

# ── Channels / Redis ───────────────────────────────────
REDIS_URL = config('REDIS_URL', default='redis://127.0.0.1:6379')

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}

# ── Auth ───────────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ── Axes ───────────────────────────────────────────────
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.25
AXES_RESET_ON_SUCCESS = True
AXES_LOCK_OUT_AT_FAILURE = True
AXES_ENABLED = True
AXES_LOCKOUT_TEMPLATE = 'accounts/locked_out.html'

# ── Session ────────────────────────────────────────────
SESSION_COOKIE_AGE = 28800
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# ── Static & Media ─────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Email ──────────────────────────────────────────────
EMAIL_BACKEND     = config('EMAIL_BACKEND',
                           default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST        = config('EMAIL_HOST',         default='localhost')
EMAIL_PORT        = config('EMAIL_PORT',         default=587,  cast=int)
EMAIL_USE_TLS     = config('EMAIL_USE_TLS',      default=True, cast=bool)
EMAIL_HOST_USER   = config('EMAIL_HOST_USER',    default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL',
                            default='J&N WMS <noreply@jandn.mw>')

# ── Site ───────────────────────────────────────────────
SITE_URL = config('SITE_URL', default='http://127.0.0.1:8000')

# ── Internationalisation ───────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Blantyre'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Crispy Forms ───────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ── Security (production) ──────────────────────────────
if not DEBUG:
    SESSION_COOKIE_SECURE  = True
    CSRF_COOKIE_SECURE     = True
    SESSION_COOKIE_HTTPONLY = True
    SECURE_HSTS_SECONDS    = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# ── Unfold Admin ───────────────────────────────────────
UNFOLD = {
    "SITE_TITLE":     "WMS Admin",
    "SITE_HEADER":    "J&N Warehouse Management",
    "SITE_SUBHEADER": "Construction & Manufacturing",
    "SITE_URL":       "/",
    "SHOW_HISTORY":   True,
    "COLORS": {
        "primary": {
            "50":  "240 249 255",
            "100": "224 242 254",
            "500": "14 165 233",
            "600": "2 132 199",
            "700": "3 105 161",
            "900": "12 74 110",
            "950": "8 47 73",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Dashboard",
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": "Inventory",
                "collapsible": True,
                "items": [
                    {"title": "Items",         "icon": "inventory_2",     "link": reverse_lazy("admin:inventory_item_changelist")},
                    {"title": "Categories",    "icon": "category",        "link": reverse_lazy("admin:inventory_category_changelist")},
                    {"title": "Warehouses",    "icon": "warehouse",       "link": reverse_lazy("admin:inventory_warehouse_changelist")},
                    {"title": "Stock Levels",  "icon": "stacked_bar_chart","link": reverse_lazy("admin:inventory_stock_changelist")},
                    {"title": "Movements",     "icon": "swap_horiz",      "link": reverse_lazy("admin:inventory_stockmovement_changelist")},
                ],
            },
            {
                "title": "Procurement",
                "collapsible": True,
                "items": [
                    {"title": "Suppliers",       "icon": "local_shipping", "link": reverse_lazy("admin:procurement_supplier_changelist")},
                    {"title": "Purchase Orders", "icon": "receipt_long",   "link": reverse_lazy("admin:procurement_purchaseorder_changelist")},
                    {"title": "Goods Receipts",  "icon": "move_to_inbox",  "link": reverse_lazy("admin:procurement_goodsreceipt_changelist")},
                ],
            },
            {
                "title": "Operations",
                "collapsible": True,
                "items": [
                    {"title": "Projects",          "icon": "construction",  "link": reverse_lazy("admin:operations_project_changelist")},
                    {"title": "Material Requests", "icon": "request_page",  "link": reverse_lazy("admin:operations_materialrequest_changelist")},
                ],
            },
            {
                "title": "Assets",
                "collapsible": True,
                "items": [
                    {"title": "Assets",      "icon": "build",        "link": reverse_lazy("admin:assets_asset_changelist")},
                    {"title": "Maintenance", "icon": "engineering",  "link": reverse_lazy("admin:assets_maintenancerecord_changelist")},
                ],
            },
            {
                "title": "Accounts",
                "collapsible": True,
                "items": [
                    {"title": "Users",         "icon": "people",              "link": reverse_lazy("admin:accounts_user_changelist")},
                    {"title": "Notifications", "icon": "notifications",       "link": reverse_lazy("admin:notifications_inappnotification_changelist")},
                ],
            },
        ],
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.security.DisallowedHost': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
