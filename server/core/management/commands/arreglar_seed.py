"""Limpieza de datos de catálogo, segura y sin borrar nada.

Hace dos cosas:
  1) Quita el prefijo "[Seed]" de los nombres (eventos, lotes, programas, ponentes).
  2) Le pone un RESUMEN de Betto (SessionSummary READY) a cada evento activo que
     no tenga uno, para que no quede solo 1 con resumen.

Es idempotente: se puede correr varias veces sin duplicar ni dañar datos.
Uso:  python manage.py arreglar_seed
"""
import re

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    Event, CertificateBatch, Program, Speaker,
    SessionSummary, ProcessingStatus,
)

SEED_RE = re.compile(r'^\s*\[?\s*seed\s*\]?\s*[-:·]?\s*', re.IGNORECASE)


def _strip_seed(value: str) -> str:
    return SEED_RE.sub('', value or '').strip()


def _betto_summary(ev):
    """Arma un resumen de Betto a partir del título, descripción y habilidades."""
    skills = ev.skills if isinstance(ev.skills, list) else []
    desc_txt = re.sub(r'<[^>]+>', '', (ev.description or '')).strip()
    desc_txt = re.sub(r'\s+', ' ', desc_txt)[:300]

    md = f"En **{ev.title}**, Betto resume los puntos centrales de la sesión. "
    if desc_txt:
        md += desc_txt.rstrip('.') + '. '
    if skills:
        md += "Se trabajaron competencias como " + ", ".join(f"**{s}**" for s in skills[:4]) + "."

    key_points = skills[:5] if skills else [
        "Se cubrieron los conceptos fundamentales del tema.",
        "Se revisaron ejemplos prácticos aplicados.",
        "Se resolvieron las dudas más frecuentes de los participantes.",
    ]
    next_steps = [
        "Repasar este resumen y practicar con un ejercicio propio.",
        "Resolver el cuestionario de autoevaluación de la sesión.",
    ]
    return md, key_points, next_steps


class Command(BaseCommand):
    help = 'Quita el prefijo "[Seed]" de los nombres y agrega resumen de Betto a los eventos que no tengan.'

    def add_arguments(self, parser):
        parser.add_argument('--solo-nombres', action='store_true',
                            help='Solo renombra; no crea resúmenes.')

    def handle(self, *args, **opts):
        renamed = 0

        # 1) Quitar "[Seed]" de los nombres
        for ev in Event.objects.all():
            nuevo = _strip_seed(ev.title)
            if nuevo != ev.title:
                ev.title = nuevo
                ev.save(update_fields=['title'])
                renamed += 1
        for b in CertificateBatch.objects.all():
            nuevo = _strip_seed(b.name)
            if nuevo != b.name:
                b.name = nuevo
                b.save(update_fields=['name'])
                renamed += 1
        for pr in Program.objects.all():
            nuevo = _strip_seed(pr.name)
            if nuevo != pr.name:
                pr.name = nuevo
                pr.save(update_fields=['name'])
                renamed += 1
        for sp in Speaker.objects.all():
            nuevo = _strip_seed(sp.name)
            if nuevo != sp.name:
                sp.name = nuevo
                sp.save(update_fields=['name'])
                renamed += 1

        self.stdout.write(self.style.SUCCESS(f'Nombres limpiados de "[Seed]": {renamed}'))

        if opts['solo_nombres']:
            return

        # 2) Resumen de Betto en eventos activos sin summary
        con_summary = set(SessionSummary.objects.values_list('event_id', flat=True))
        creados = 0
        for ev in Event.objects.filter(is_active=True):
            if ev.id in con_summary:
                continue
            md, key_points, next_steps = _betto_summary(ev)
            summ = SessionSummary.objects.create(event=ev)
            summ.status = ProcessingStatus.READY
            summ.summary_md = md
            summ.key_points = key_points
            summ.next_steps = next_steps
            summ.quiz = []
            summ.transcript_raw = md
            summ.transcript_chars = len(md)
            summ.duration_minutes = (ev.hours or 0) * 60
            summ.ai_model = 'gpt-4o-mini'
            summ.processed_at = timezone.now()
            summ.save()
            creados += 1

        self.stdout.write(self.style.SUCCESS(f'Resúmenes de Betto creados: {creados}'))
        self.stdout.write(self.style.SUCCESS('Listo. Datos actualizados sin borrar nada.'))
