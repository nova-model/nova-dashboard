service nginx restart
poetry run python manage.py migrate
poetry run python -m gunicorn src.launcher_app.asgi:application -k uvicorn.workers.UvicornWorker -w 4
