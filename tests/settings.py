"""Settings mínimos para rodar os testes do app sem o GeoNode: python runtests.py"""
import pathlib
import tempfile

BASE_DIR = pathlib.Path(__file__).resolve().parent

SECRET_KEY = "tests"
DEBUG = False
USE_TZ = True
SITE_ID = 1
ROOT_URLCONF = "tests.urls"
LANGUAGE_CODE = "en"
USE_I18N = True

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.flatpages",
    "tinymce",
    "geonode_flatpages_editor",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # templates/geonode_base.html: substituto mínimo do template base do GeoNode
        "DIRS": [BASE_DIR / "templates"],
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

STATIC_URL = "/static/"
MEDIA_URL = "/uploaded/"
MEDIA_ROOT = tempfile.mkdtemp(prefix="flatpages-editor-tests-")
