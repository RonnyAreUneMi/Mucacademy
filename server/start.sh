#!/bin/sh
# Arranque en Railway: espera a que la red privada de la base esté lista
# (reintenta migrate), importa los datos iniciales una sola vez, y levanta gunicorn.

until python manage.py migrate --noinput; do
  echo "DB no lista, reintento en 3s..."
  sleep 3
done

python manage.py import_data || true

exec gunicorn config.wsgi:application \
  --bind "[::]:8000" \
  --workers 1 \
  --timeout 120 \
  --log-file - \
  --access-logfile - \
  --log-level info
