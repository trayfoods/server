from __future__ import absolute_import, unicode_literals
import os

from celery import Celery
from django.conf import settings
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trayapp.settings")

app = Celery("trayapp", broker=settings.CELERY_BROKER_URL)
# add broker_connection_retry_on_startup
app.conf.enable_utc = False

app.conf.update(timezone="Africa/Lagos")

app.config_from_object(settings, namespace="CELERY")

# Celery Beat Settings
app.conf.beat_schedule = {
    'settle-transactions-every-hour': {
        'task': 'users.tasks.settle_transactions',
        'schedule': crontab(minute=0, hour='*'),  # runs at the top of every hour
    },
}

app.autodiscover_tasks()

app.conf.broker_connection_retry_on_startup = True
