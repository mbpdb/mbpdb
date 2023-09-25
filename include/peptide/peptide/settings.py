"""
Django settings for peptide project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

import os, re

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ')^j4*39ghmd&wz-@w2qwe!to989(#7*(0*v^(4kk1^!k@_t_y*'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ['128.193.11.196', '127.0.0.1', 'localhost', '192.84.190.235', 'mbpdb.nws.oregonstate.edu','mbpdbcontainer.lemonisland-71b15397.westus3.azurecontainerapps.io']


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'peptide',
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

CSRF_TRUSTED_ORIGINS = ['https://mbpdbcontainer.lemonisland-71b15397.westus3.azurecontainerapps.io','https://mbpdb.nws.oregonstate.edu']


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

STATIC_ROOT = os.path.join(BASE_DIR, 'static_files')

STATIC_URL = '/static/'

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
