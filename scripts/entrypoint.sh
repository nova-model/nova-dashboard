cd /opt/run/vue
pnpm build
cp /opt/run/tools/tools.json dist/tools.json

cd /opt/run/django
envsubst '$UCAMS_REDIRECT_PATH $XCAMS_REDIRECT_PATH' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
service nginx restart
poetry run python manage.py migrate
poetry run python -m gunicorn src.launcher_app.asgi:application -k uvicorn.workers.UvicornWorker -w 4
