# celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.signals import worker_init

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'peptide.settings')

app = Celery('peptide', broker='redis://redis:6379/0')

app.config_from_object('django.conf:settings', namespace='CELERY')

@worker_init.connect
def worker_init(**kwargs):
    # Drop privileges when worker starts
    try:
        import pwd
        celery_user = pwd.getpwnam('celery_user')
        os.setuid(celery_user.pw_uid)
    except (ImportError, KeyError):
        pass

app.autodiscover_tasks()