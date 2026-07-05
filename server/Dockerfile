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

# Arranque robusto (Railway/local):
#  1) migrate  2) superusuario (con timeout: si se cuelga, no bloquea)
#  3) gunicorn en $PORT (fallback 8000 local), 2 workers para no pasarnos de RAM.
# Shell-form para que ${PORT} se expanda. docker-compose override este CMD.
CMD sh -c "python manage.py migrate --noinput && (timeout 30 python manage.py create_default_superuser || true) && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120 --log-file - --access-logfile -"
