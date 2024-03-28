# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

import os
import os.path
import sys
from datetime import timedelta


BASE_DIR = os.path.dirname(os.path.dirname(__file__))

APPEND_SLASH = False
ALLOWED_HOSTS = ["*"]

ADMINS = (
    ("Admin", "example@example.com"),
)

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "taiga",
        "USER": "taiga",
        "PASSWORD": "taiga",
        "HOST": "127.0.0.1"
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake"
    }
}

INSTANCE_TYPE = "SRC"

# CELERY
CELERY_ENABLED = False
from kombu import Queue  # noqa

CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'
CELERY_RESULT_BACKEND = None # for a general installation, we don't need to store the results
CELERY_ACCEPT_CONTENT = ['pickle', ]  # Values are 'pickle', 'json', 'msgpack' and 'yaml'
CELERY_TASK_SERIALIZER = "pickle"
CELERY_RESULT_SERIALIZER = "pickle"
CELERY_TIMEZONE = 'Europe/Madrid'
CELERY_TASK_DEFAULT_QUEUE = 'tasks'
CELERY_QUEUES = (
    Queue('tasks', routing_key='task.#'),
    Queue('transient', routing_key='transient.#', delivery_mode=1)
)
CELERY_TASK_DEFAULT_EXCHANGE = 'tasks'
CELERY_TASK_DEFAULT_EXCHANGE_TYPE = 'topic'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'task.default'


PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# Default configuration for reverse proxy
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Errors report configuration
SEND_BROKEN_LINK_EMAILS = True
IGNORABLE_404_ENDS = (".php", ".cgi")
IGNORABLE_404_STARTS = ("/phpmyadmin/",)

ATOMIC_REQUESTS = True
TIME_ZONE = "UTC"
LOGIN_URL = "/auth/login/"
USE_TZ = True

USE_I18N = True
USE_L10N = True
# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# Languages we provide translations for, out of the box.
LANGUAGES = [
    #("af", "Afrikaans"),  # Afrikaans
    ("ar", "العربية‏"),  # Arabic
    #("ast", "Asturiano"),  # Asturian
    #("az", "Azərbaycan dili"),  # Azerbaijani
    #("bg", "Български"),  # Bulgarian
    #("be", "Беларуская"),  # Belarusian
    #("bn", "বাংলা"),  # Bengali
    #("br", "Bretón"),  # Breton
    #("bs", "Bosanski"),  # Bosnian
    ("ca", "Català"),  # Catalan
    # ("cs", "Čeština"),  # Czech
    # ("cy", "Cymraeg"),  # Welsh
    ("da", "Dansk"),  # Danish
    ("de", "Deutsch"),  # German
    # ("el", "Ελληνικά"),  # Greek
    ("en", "English (US)"),  # English
    # ("en-au", "English (Australia)"),  # Australian English
    # ("en-gb", "English (UK)"),  # British English
    # ("eo", "esperanta"),  # Esperanto
    ("es", "Español"),  # Spanish
    # ("es-ar", "Español (Argentina)"),  # Argentinian Spanish
    # ("es-mx", "Español (México)"),  # Mexican Spanish
    # ("es-ni", "Español (Nicaragua)"),  # Nicaraguan Spanish
    # ("es-ve", "Español (Venezuela)"),  # Venezuelan Spanish
    # ("et", "Eesti"),  # Estonian
    ("eu", "Euskara"),  # Basque
    ("fa", "فارسی‏"),  # Persian
    ("fi", "Suomi"),  # Finnish
    ("fr", "Français"),  # French
    # ("fy", "Frysk"),  # Frisian
    # ("ga", "Irish"),  # Irish
    # ("gl", "Galego"),  # Galician
    ("he", "עברית‏"),  # Hebrew
    # ("hi", "हिन्दी"),  # Hindi
    # ("hr", "Hrvatski"),  # Croatian
    # ("hu", "Magyar"),  # Hungarian
    # ("ia", "Interlingua"),  # Interlingua
    # ("id", "Bahasa Indonesia"),  # Indonesian
    # ("io", "IDO"),  # Ido
    # ("is", "Íslenska"),  # Icelandic
    ("it", "Italiano"),  # Italian
    ("ja", "日本語"),  # Japanese
    # ("ka", "ქართული"),  # Georgian
    # ("kk", "Қазақша"),  # Kazakh
    # ("km", "ភាសាខ្មែរ"),  # Khmer
    # ("kn", "ಕನ್ನಡ"),  # Kannada
    ("ko", "한국어"),  # Korean
    # ("lb", "Lëtzebuergesch"),  # Luxembourgish
    # ("lt", "Lietuvių"),  # Lithuanian
    ("lv", "Latviešu"),  # Latvian
    # ("mk", "Македонски"),  # Macedonian
    # ("ml", "മലയാളം"),  # Malayalam
    # ("mn", "Монгол"),  # Mongolian
    # ("mr", "मराठी"),  # Marathi
    # ("my", "မြန်မာ"),  # Burmese
    ("nb", "Norsk (bokmål)"),  # Norwegian Bokmal
    # ("ne", "नेपाली"),  # Nepali
    ("nl", "Nederlands"),  # Dutch
    # ("nn", "Norsk (nynorsk)"),  # Norwegian Nynorsk
    # ("os", "Ирон æвзаг"),  # Ossetic
    # ("pa", "ਪੰਜਾਬੀ"),  # Punjabi
    ("pl", "Polski"),  # Polish
    # ("pt", "Português (Portugal)"),  # Portuguese
    ("pt-br", "Português (Brasil)"),  # Brazilian Portuguese
    # ("ro", "Română"),  # Romanian
    ("ru", "Русский"),  # Russian
    # ("sk", "Slovenčina"),  # Slovak
    # ("sl", "Slovenščina"),  # Slovenian
    # ("sq", "Shqip"),  # Albanian
    ("sr", "Српски"),  # Serbian
    # ("sr-latn", "srpski"),  # Serbian Latin
    ("sv", "Svenska"),  # Swedish
    # ("sw", "Kiswahili"),  # Swahili
    # ("ta", "தமிழ்"),  # Tamil
    # ("te", "తెలుగు"),  # Telugu
    # ("th", "ภาษาไทย"),  # Thai
    ("tr", "Türkçe"),  # Turkish
    # ("tt", "татар теле"),  # Tatar
    # ("udm", "удмурт кыл"),  # Udmurt
    ("uk", "Українська"),  # Ukrainian
    # ("ur", "اردو‏"),  # Urdu
    ("vi", "Tiếng Việt"),  # Vietnamese
    ("zh-hans", "中文(简体)"),  # Simplified Chinese
    ("zh-hant", "中文(香港)"),  # Traditional Chinese
]

# Languages using BiDi (right-to-left) layout
LANGUAGES_BIDI = ["he", "ar", "fa", "ur"]

LOCALE_PATHS = (
    os.path.join(BASE_DIR, "locale"),
    os.path.join(BASE_DIR, "taiga", "locale"),
)

SITES = {
    "api": {"domain": "localhost:8000", "scheme": "http", "name": "api"},
    "front": {"domain": "localhost:9001", "scheme": "http", "name": "front"},
}

SITE_ID = "api"

# Session and CSRF configuration
SESSION_ENGINE = "django.contrib.sessions.backends.db"
# SESSION_COOKIE_AGE = 1209600  # (2 weeks) and set SESSION_EXPIRE_AT_BROWSER_CLOSE to false
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_AGE = None
CSRF_COOKIE_SECURE = True

# MAIL OPTIONS
DEFAULT_FROM_EMAIL = "john@doe.com"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# 0 notifications will work in a synchronous way
# >0 an external process will check the pending notifications and will send them
# collapsed during that interval
CHANGE_NOTIFICATIONS_MIN_INTERVAL = 0  # seconds
SEND_BULK_EMAILS_WITH_CELERY = True

DJMAIL_REAL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DJMAIL_SEND_ASYNC = True
DJMAIL_MAX_RETRY_NUMBER = 3
DJMAIL_TEMPLATE_EXTENSION = "jinja"

# Events backend
EVENTS_PUSH_BACKEND = "taiga.events.backends.postgresql.EventsPushBackend"
# EVENTS_PUSH_BACKEND = "taiga.events.backends.rabbitmq.EventsPushBackend"
# EVENTS_PUSH_BACKEND_OPTIONS = {"url": "//guest:guest@127.0.0.1/"}

# Message System
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# The absolute url is mandatory because attachments
# urls depends on it. On production should be set
# something like https://media.taiga.io/
MEDIA_URL = "http://localhost:8000/media/"
STATIC_URL = "http://localhost:8000/static/"

# Static configuration.
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
STATIC_ROOT = os.path.join(BASE_DIR, "static")

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Don't forget to use absolute paths, not relative paths.
)

# Default storage
DEFAULT_FILE_STORAGE = "taiga.base.storage.FileSystemStorage"

FILE_UPLOAD_PERMISSIONS = 0o644

SECRET_KEY = "aw3+t2r(8(0kkrhg8)gx6i96v5^kv%6cfep9wxfom0%7dy0m9e"

TEMPLATES = [
    {
        "BACKEND": "django_jinja.backend.Jinja2",
        "DIRS": [
            os.path.join(BASE_DIR, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            'context_processors': [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
            "match_extension": ".jinja",
        }
    },
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            'context_processors': [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
        }
    },
]


MIDDLEWARE = [
    "taiga.base.middleware.cors.CorsMiddleware",
    "taiga.events.middleware.SessionIDMiddleware",

    # Common middlewares
    "django.middleware.common.CommonMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Only needed by django admin
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]


ROOT_URLCONF = "taiga.urls"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.postgres",

    "taiga.base",
    "taiga.base.api",
    "taiga.locale",
    "taiga.events",
    "taiga.front",
    "taiga.users",
    "taiga.userstorage",
    "taiga.auth.token_denylist",
    "taiga.external_apps",
    "taiga.projects",
    "taiga.projects.references",
    "taiga.projects.custom_attributes",
    "taiga.projects.history",
    "taiga.projects.notifications",
    "taiga.projects.attachments",
    "taiga.projects.likes",
    "taiga.projects.votes",
    "taiga.projects.milestones",
    "taiga.projects.epics",
    "taiga.projects.userstories",
    "taiga.projects.tasks",
    "taiga.projects.issues",
    "taiga.projects.wiki",
    "taiga.projects.contact",
    "taiga.projects.settings",
    "taiga.searches",
    "taiga.timeline",
    "taiga.mdrender",
    "taiga.export_import",
    "taiga.feedback",
    "taiga.stats",
    "taiga.hooks.github",
    "taiga.hooks.gitlab",
    "taiga.hooks.bitbucket",
    "taiga.hooks.gogs",
    "taiga.webhooks",
    "taiga.importers",

    "djmail",
    "django_jinja",
    "django_jinja.contrib._humanize",
    "sr",
    "easy_thumbnails",
    "raven.contrib.django.raven_compat",
]

WSGI_APPLICATION = "taiga.wsgi.application"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse"
        }
    },
    "formatters": {
        "complete": {
            "format": "%(levelname)s:%(asctime)s:%(module)s %(message)s"
        },
        "simple": {
            "format": "%(levelname)s:%(asctime)s: %(message)s"
        },
        "null": {
            "format": "%(message)s",
        },
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[%(server_time)s] %(message)s",
        },
    },
    "handlers": {
        "null": {
            "level": "DEBUG",
            "class": "logging.NullHandler",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "taiga.base.utils.logs.CustomAdminEmailHandler",
        },
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["null"],
            "level": "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["mail_admins", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
        "MARKDOWN": {
            "handlers": ["null"],
            "level": "INFO",
            "propagate": False,
        },
        "taiga.export_import": {
            "handlers": ["mail_admins", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "taiga": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    }
}


AUTH_USER_MODEL = "users.User"

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=8),
    'CANCEL_TOKEN_LIFETIME': timedelta(days=100),
}

FLUSH_REFRESHED_TOKENS_PERIODICITY = 3 * 24 * 3600 # seconds

FORMAT_MODULE_PATH = "taiga.base.formats"

DATE_INPUT_FORMATS = (
    "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%b %d %Y",
    "%b %d, %Y", "%d %b %Y", "%d %b, %Y", "%B %d %Y",
    "%B %d, %Y", "%d %B %Y", "%d %B, %Y"
)

# Authentication settings (only for django admin)
AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",  # default
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # Mainly used by taiga-front
        'taiga.auth.authentication.JWTAuthentication',

        # Mainly used for api debug.
        "taiga.auth.backends.Session",

        # Application tokens auth
        "taiga.external_apps.auth_backends.Token",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "taiga.base.throttling.CommonThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon-write": None,
        "user-write": None,
        "anon-read": None,
        "user-read": None,
        "import-mode": None,
        "import-dump-mode": "1/minute",
        "create-memberships": None,
        "login-fail": None,
        "register-success": None,
        "user-detail": None,
        "user-update": None,
    },
    "DEFAULT_THROTTLE_WHITELIST": [],
    "FILTER_BACKEND": "taiga.base.filters.FilterBackend",
    "EXCEPTION_HANDLER": "taiga.base.exceptions.exception_handler",
    "PAGINATE_BY": 30,
    "PAGINATE_BY_PARAM": "page_size",
    "MAX_PAGINATE_BY": 1000,
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z"
}

# Extra expose header related to Taiga APP (see taiga.base.middleware.cors=)
APP_EXTRA_EXPOSE_HEADERS = [
    "taiga-info-total-opened-milestones",
    "taiga-info-total-closed-milestones",
    "taiga-info-backlog-total-userstories",
    "taiga-info-userstories-without-swimlane",
    "taiga-info-project-memberships",
    "taiga-info-project-is-private",
    "taiga-info-order-updated"
]

DEFAULT_PROJECT_TEMPLATE = "scrum"
# Setting DEFAULT_PROJECT_SLUG_PREFIX to false removes the username from project slug
DEFAULT_PROJECT_SLUG_PREFIX = True
PUBLIC_REGISTER_ENABLED = False
# None or [] values in USER_EMAIL_ALLOWED_DOMAINS means allow any domain
USER_EMAIL_ALLOWED_DOMAINS = None

PRIVATE_USER_PROFILES = False

SEARCHES_MAX_RESULTS = 150

SOUTH_MIGRATION_MODULES = {
    'easy_thumbnails': 'easy_thumbnails.south_migrations',
}


THN_AVATAR_SIZE = 80                # 80x80 pixels
THN_AVATAR_BIG_SIZE = 300           # 300x300 pixels
THN_LOGO_SMALL_SIZE = 80            # 80x80 pixels
THN_LOGO_BIG_SIZE = 300             # 300x300 pixels
THN_TIMELINE_IMAGE_SIZE = 640       # 640x??? pixels
THN_CARD_IMAGE_WIDTH = 300          # 300 pixels
THN_CARD_IMAGE_HEIGHT = 200         # 200 pixels
THN_PREVIEW_IMAGE_WIDTH = 800       # 800 pixels

THN_AVATAR_SMALL = "avatar"
THN_AVATAR_BIG = "big-avatar"
THN_LOGO_SMALL = "logo-small"
THN_LOGO_BIG = "logo-big"
THN_ATTACHMENT_TIMELINE = "timeline-image"
THN_ATTACHMENT_CARD = "card-image"
THN_ATTACHMENT_PREVIEW = "preview-image"

THUMBNAIL_ALIASES = {
    "": {
        THN_AVATAR_SMALL: {"size": (THN_AVATAR_SIZE, THN_AVATAR_SIZE), "crop": True},
        THN_AVATAR_BIG: {"size": (THN_AVATAR_BIG_SIZE, THN_AVATAR_BIG_SIZE), "crop": True},
        THN_LOGO_SMALL: {"size": (THN_LOGO_SMALL_SIZE, THN_LOGO_SMALL_SIZE), "crop": True},
        THN_LOGO_BIG: {"size": (THN_LOGO_BIG_SIZE, THN_LOGO_BIG_SIZE), "crop": True},
        THN_ATTACHMENT_TIMELINE: {"size": (THN_TIMELINE_IMAGE_SIZE, 0), "crop": True},
        THN_ATTACHMENT_CARD: {"size": (THN_CARD_IMAGE_WIDTH, THN_CARD_IMAGE_HEIGHT), "crop": True},
        THN_ATTACHMENT_PREVIEW: {"size": (THN_PREVIEW_IMAGE_WIDTH, 0), "crop": False},
    },
}

# Feedback module settings
FEEDBACK_ENABLED = True
FEEDBACK_EMAIL = "support@taiga.io"

# Stats module settings
STATS_ENABLED = False
STATS_CACHE_TIMEOUT = 60 * 60  # In second

# List of functions called for filling correctly the ProjectModulesConfig associated to a project
# This functions should receive a Project parameter and return a dict with the desired configuration
PROJECT_MODULES_CONFIGURATORS = {
    "github": "taiga.hooks.github.services.get_or_generate_config",
    "gitlab": "taiga.hooks.gitlab.services.get_or_generate_config",
    "bitbucket": "taiga.hooks.bitbucket.services.get_or_generate_config",
    "gogs": "taiga.hooks.gogs.services.get_or_generate_config",
}

# Official BitBucket valid IPs are https://confluence.atlassian.com/cloud/atlassian-cloud-ip-ranges-and-domains-744721662.html#AtlassiancloudIPrangesanddomains-OutgoingConnections
BITBUCKET_VALID_ORIGIN_IPS = [
    "13.52.5.96/28",
    "13.236.8.224/28",
    "18.184.99.224/28",
    "18.234.32.224/28",
    "18.246.31.224/28",
    "52.215.192.224/28",
    "104.192.137.240/28",
    "104.192.138.240/28",
    "104.192.140.240/28",
    "104.192.142.240/28",
    "104.192.143.240/28",
    "185.166.143.240/28",
    "185.166.142.240/28"
]

GITLAB_VALID_ORIGIN_IPS = []

EXPORTS_TTL = 60 * 60 * 24  # 24 hours

WEBHOOKS_ENABLED = False
WEBHOOKS_ALLOW_PRIVATE_ADDRESS = False
WEBHOOKS_ALLOW_REDIRECTS = False

# If is True /front/sitemap.xml show a valid sitemap of taiga-front client
FRONT_SITEMAP_ENABLED = False
FRONT_SITEMAP_CACHE_TIMEOUT = 24 * 60 * 60  # In second
FRONT_SITEMAP_PAGE_SIZE = 25000


EXTRA_BLOCKING_CODES = []

MAX_PRIVATE_PROJECTS_PER_USER = None  # None == no limit
MAX_PUBLIC_PROJECTS_PER_USER = None  # None == no limit
MAX_MEMBERSHIPS_PRIVATE_PROJECTS = None  # None == no limit
MAX_MEMBERSHIPS_PUBLIC_PROJECTS = None  # None == no limit

MAX_PENDING_MEMBERSHIPS = 30  # Max number of unconfirmed memberships in a project

# DJANGO SETTINGS RESOLVER
SR = {
    "taigaio_url": "https://taiga.io",
    "social": {
        "twitter_url": "https://twitter.com/taigaio",
        "github_url": "https://github.com/taigaio",
    },
    "support": {
        "url": "https://tree.taiga.io/support/",
        "email": "support@taiga.io"
    },
    "signature": "The Taiga Team",
    "product_name": "Taiga",
}

IMPORTERS = {
    "github": {
        "active": False,
        "client_id": "",
        "client_secret": "",
    },
    "trello": {
        "active": False,
        "api_key": "",
        "secret_key": "",
    },
    "jira": {
        "active": False,
        "consumer_key": "",
        "cert": "",
        "pub_cert": "",
    },
    "asana": {
        "active": False,
        "callback_url": "",
        "app_id": "",
        "app_secret": "",
    }
}

# Configuration for sending notifications
NOTIFICATIONS_CUSTOM_FILTER = False

# MDRENDER
MDRENDER_CACHE_ENABLE = True
MDRENDER_CACHE_MIN_SIZE = 40
MDRENDER_CACHE_TIMEOUT = 86400

# TELEMETRY

ENABLE_TELEMETRY = True
RUDDER_WRITE_KEY = "1kmTTxJoSmaZNRpU1uORpyZ8mqv"
DATA_PLANE_URL = "https://telemetry.taiga.io/"
INSTALLED_APPS += [
        "taiga.telemetry"
]

# NOTE: DON'T INSERT ANYTHING AFTER THIS BLOCK
TEST_RUNNER = "django.test.runner.DiscoverRunner"

if "test" in sys.argv:
    print("\033[1;91mNo django tests.\033[0m")
    print("Try: \033[1;33mpy.test\033[0m")
    sys.exit(0)
# NOTE: DON'T INSERT MORE SETTINGS AFTER THIS LINE
