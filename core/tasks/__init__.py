"""Tasks de Celery del app `core`.

Importamos los submódulos aquí para que `app.autodiscover_tasks()` los
registre al arrancar el worker (sin necesidad de que algún `views.py` los
importe primero).
"""
from . import email_tasks, transcript_tasks, program_tasks  # noqa: F401
