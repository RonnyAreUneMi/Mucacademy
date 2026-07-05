"""Configuración de Celery para tareas asíncronas (envíos masivos, PDFs, IA).

Uso desde código Django:
    from core.tasks.email_tasks import send_certificate_issued_bulk
    send_certificate_issued_bulk.delay(batch_id=42)

Worker en otra terminal:
    celery -A config worker -l info
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('certifai')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
