"""
Django settings for peptide project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))



# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ')^j4*39ghmd&wz-@w2qwe!to989(#7*(0*v^(4kk1^!k@_t_y*'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ['128.193.11.196']


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

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'peptide.urls'

WSGI_APPLICATION = 'peptide.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

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


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'static_files')

STATIC_URL = '/static/'

SENDFILE_BACKEND = 'sendfile.backends.simple'

MEDIA_ROOT = os.path.join(BASE_DIR, 'uploads')

WORK_DIRECTORY = os.path.join(BASE_DIR, 'uploads/temp')
XLS_TO_TSV = os.path.join(BASE_DIR, 'scripts/xlsx_to_tsv.pl')
CREATE_FASTA_LIB = os.path.join(BASE_DIR, 'scripts/create_fasta_lib.pl')
CREATE_FASTA_INPUT = os.path.join(BASE_DIR, 'scripts/create_fasta_input.pl')
COMBINE = os.path.join(BASE_DIR, 'scripts/combine.pl')
SKYLINE = os.path.join(BASE_DIR, 'scripts/skyline_combine.pl')
SKYLINE_AUTO = os.path.join(BASE_DIR, 'scripts/skyline_combine_rearranged.pl')
FILTER = os.path.join(BASE_DIR, 'scripts/skyline_filter.pl')
SKYLINE_EDIT = os.path.join(BASE_DIR, 'scripts/skyline_edit_columns.pl')
REMOVE_DOMAINS = os.path.join(BASE_DIR, 'scripts/remove_domains_xml.pl')
COMBINE_PEPTIDES = os.path.join(BASE_DIR, 'scripts/skyline_combine_peptides_with_same_mods.pl')
PEPEX = os.path.join(BASE_DIR, 'scripts/pepex.pl')
FASTA_FILES_DIR = os.path.join(BASE_DIR,'scripts/fasta_files')
FIX_WEIRD_CHARS = os.path.join(BASE_DIR, 'scripts/fix_weird_chars.pl')

#for search translation
TRANSLATE_LIST = [
    ['cow','bos taurus','bovine'],
    ['sheep','ovis aries','ovine'],
    ['goat','capra hircus','caprine'],
    ['pig','sus scrofa','porcine'],
    ['yak','bos mutus'],
    ['rabbit','oryctolagus cuniculus'],
    ['donkey','equus asinus'],
    ['human','homo sapiens']
]


#mail settings
EMAIL_HOST = 'smtp.oregonstate.edu'
EMAIL_PORT = 25
NOREPLY_EMAIL = 'noreply@mbpdb.nws.oregonstate.edu'
