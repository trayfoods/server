export LANG=C.UTF-8

python manage.py runserver 0.0.0.0:8000 & celery -A trayapp worker -l INFO -B