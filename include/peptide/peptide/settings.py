"""
Django settings for peptide project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""
from celery import Celery
import os, re

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY must be set as an environment variable (DJANGO_SECRET_KEY)
# Generate a new key with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# Allow build-time operations (like collectstatic) without the real key
# The real key MUST be set at runtime for the app to function securely
_BUILDING = os.environ.get('BUILDING', 'false').lower() == 'true'


if not SECRET_KEY:
    if _BUILDING:
        # Use a temporary key for build-time operations only (collectstatic, etc.)
        SECRET_KEY = 'build-time-temporary-key-not-for-production'
    else:
        raise ValueError(
            "DJANGO_SECRET_KEY environment variable is not set. "
       )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# ALLOWED_HOSTS loaded from environment variable (comma-separated)
# Set DJANGO_ALLOWED_HOSTS in your environment or GitHub Secrets
# Example: DJANGO_ALLOWED_HOSTS=mbpdb.nws.oregonstate.edu,localhost,127.0.0.1
_default_hosts = ['127.0.0.1', 'localhost']
_env_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
_extra_hosts = [h.strip() for h in _env_hosts.split(',') if h.strip()] if _env_hosts else []
ALLOWED_HOSTS = _default_hosts + _extra_hosts


# Celery settings
CELERY_WORKER_USER = 'celery_user'
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_SOFT_TIME_LIMIT = 600  # 10 minutes
CELERY_TASK_TIME_LIMIT = 600  # 10 minutes

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',  # Default local Redis server
        'TIMEOUT': 600,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'peptide',
    'django_celery_progress',
)
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
]
# CORS and CSRF origins - production URLs loaded from environment
# Set DJANGO_CORS_ORIGINS in your environment (comma-separated)
# Example: DJANGO_CORS_ORIGINS=https://mbpdb.nws.oregonstate.edu,https://myapp.azurecontainerapps.io
_default_cors = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    # Voila instances (local)
    "http://localhost:8866",
    "http://127.0.0.1:8866",
    "http://localhost:8867",
    "http://127.0.0.1:8867",
    "http://localhost:8868",
    "http://127.0.0.1:8868",
]
_env_cors = os.environ.get('DJANGO_CORS_ORIGINS', '')
_extra_cors = [h.strip() for h in _env_cors.split(',') if h.strip()] if _env_cors else []
CORS_ALLOWED_ORIGINS = _default_cors + _extra_cors

_default_csrf = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    # Voila instances (local)
    "http://localhost:8866",
    "http://127.0.0.1:8866",
    "http://localhost:8867",
    "http://127.0.0.1:8867",
    "http://localhost:8868",
    "http://127.0.0.1:8868",
]
_env_csrf = os.environ.get('DJANGO_CSRF_ORIGINS', '')
_extra_csrf = [h.strip() for h in _env_csrf.split(',') if h.strip()] if _env_csrf else []
CSRF_TRUSTED_ORIGINS = _default_csrf + _extra_csrf


ROOT_URLCONF = 'peptide.urls'

WSGI_APPLICATION = 'peptide.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

FILE_UPLOAD_HANDLERS = (
#                         "django.core.files.uploadhandler.MemoryFileUploadHandler",
                        "django.core.files.uploadhandler.TemporaryFileUploadHandler",
                        )

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Los_Angeles'

USE_I18N = True

USE_L10N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "peptide/static"),  # Keep this as your main static directory
]

# Make sure these paths are correct
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static_files')


STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

SENDFILE_BACKEND = 'sendfile.backends.simple'

MEDIA_ROOT = os.path.join(BASE_DIR, 'uploads')

WORK_DIRECTORY = os.path.join(BASE_DIR, 'uploads/temp')
XLS_TO_TSV = os.path.join(BASE_DIR, 'scripts/xlsx_to_tsv.pl')
CREATE_FASTA_LIB = os.path.join(BASE_DIR, 'scripts/create_fasta_lib.pl')
CREATE_FASTA_INPUT = os.path.join(BASE_DIR, 'scripts/create_fasta_input.pl')
COMBINE = os.path.join(BASE_DIR, 'scripts/combine.pl')
PEPEX = os.path.join(BASE_DIR, 'scripts/pepex.pl')
FASTA_FILES_DIR = os.path.join(BASE_DIR,'scripts/fasta_files')
FIX_WEIRD_CHARS = os.path.join(BASE_DIR, 'scripts/fix_weird_chars.pl')
BLAST_DB = os.path.join(BASE_DIR,'peptide/blast_db')

#for species search translation
SPEC_TRANSLATE_LIST = [
    ['human', 'homo sapiens'],
    ['cow', 'bos taurus'],
    ['sheep', 'ovis aries'],
    ['goat', 'capra hircus'],
    ['pig', 'sus scrofa'],
    ['yak', 'bos mutus'],
    ['rabbit', 'oryctolagus cuniculus'],
    ['donkey', 'equus asinus'],
    ['camel', 'camelus dromedarius'],
    ['buffalo', 'bubalus bubalis']
    #['horse', 'Equus caballus'], no records in db
    #['rat', 'Rattus norvegicus'], no records in db
    #['fallow deer', 'dama dama'], no records in db
    #['red deer', 'cervus elaphus'], no records in db
    #['reindeer', 'rangifer tarandus'], no records in db
    #['american bison', 'bison bison'], no records in db
    #['elephant', 'elephas maximus'], no records in db
    #['mouse', 'mus musculus'], no records in db
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
"""
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',  # Path to your log file
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
"""