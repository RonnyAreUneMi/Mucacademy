# Imagen base liviana con Python 3.12
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependencias del sistema mínimas — psycopg2 necesita libpq, reportlab/pillow necesitan libs gráficas
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache de capas: requirements primero, código después
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# Default: migra y levanta gunicorn en el puerto que provee el entorno ($PORT en
# Railway; 8000 local). Shell-form para que ${PORT} se expanda.
# docker-compose override este CMD para web/worker/beat.
CMD sh -c "python manage.py migrate --noinput && python manage.py create_default_superuser && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 60 --log-file -"
