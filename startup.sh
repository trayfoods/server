export LANG=C.UTF-8

gunicorn — bind=0.0.0.0 — timeout 600 trayapp.wsgi & celery -A trayapp worker -l INFO -B