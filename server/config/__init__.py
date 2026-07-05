"""Hace que Celery se inicialice con Django.

`celery_app` es importado para que `@shared_task` funcione en cualquier app
sin tener que importar el módulo celery explícitamente.
"""
from .celery import app as celery_app

__all__ = ('celery_app',)
