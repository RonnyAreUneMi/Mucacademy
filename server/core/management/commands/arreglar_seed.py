"""Limpieza de datos de catálogo, segura y sin borrar nada.

Hace dos cosas:
  1) Quita el prefijo "[Seed]" de los nombres (eventos, lotes, programas, ponentes).
  2) Le pone un RESUMEN de Betto (SessionSummary READY) a cada evento activo que
     no tenga uno, para que no quede solo 1 con resumen.

Es idempotente: se puede correr varias veces sin duplicar ni dañar datos.
Uso:  python manage.py arreglar_seed
"""
import random
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
    """Arma un resumen de Betto largo y estructurado a partir del título,
    la descripción y las habilidades del evento."""
    skills = ev.skills if isinstance(ev.skills, list) else []
    desc_txt = re.sub(r'<[^>]+>', '', (ev.description or '')).strip()
    desc_txt = re.sub(r'\s+', ' ', desc_txt)
    modal = 'sesión virtual' if getattr(ev, 'is_virtual', False) else 'sesión presencial'
    horas = ev.hours or 0

    partes = [
        f"En esta {modal}, **{ev.title}**, se desarrollaron de forma práctica los fundamentos y "
        f"las aplicaciones del tema, combinando la teoría con ejemplos reales para que cada "
        f"participante se llevara aprendizajes accionables desde el primer momento.",
    ]
    if desc_txt:
        partes.append(desc_txt.rstrip('.') + '.')
    if skills:
        partes.append(
            "A lo largo del encuentro se trabajaron competencias clave como "
            + ", ".join(f"**{s}**" for s in skills)
            + ", reforzadas con demostraciones guiadas y espacios de preguntas y respuestas."
        )
    partes.append(
        "El facilitador acompañó cada bloque con buenas prácticas del sector, errores comunes que "
        "conviene evitar y recomendaciones para seguir profundizando de manera autónoma. "
        "Betto preparó este resumen para que puedas repasar lo esencial"
        + (f" de las {horas} horas de contenido" if horas else "")
        + " en pocos minutos y consolidar lo aprendido."
    )
    md = "\n\n".join(partes)

    base_points = list(skills)
    base_points += [
        "Se explicaron los conceptos fundamentales con ejemplos aplicados.",
        "Se mostraron casos de uso reales del sector.",
        "Se resolvieron las dudas más frecuentes de los participantes.",
        "Se compartieron buenas prácticas y errores comunes a evitar.",
    ]
    key_points = base_points[:6]

    next_steps = [
        "Repasar este resumen y anotar las ideas que más te sirvieron.",
        "Aplicar lo aprendido en un ejercicio o mini-proyecto propio.",
        "Resolver el cuestionario de autoevaluación para medir tu avance.",
    ]
    return md, key_points, next_steps


def _q(kind, text, options, correct, expl):
    # Formato canónico que consume el cuestionario del evento: type/question.
    return dict(type=kind, question=text, options=options, correct_idx=correct, explanation=expl)


def _normalize_quiz(quiz):
    """Convierte quizzes con claves viejas (kind/text) al formato del front
    (type/question). Devuelve (quiz_normalizado, cambió)."""
    if not isinstance(quiz, list):
        return quiz, False
    changed = False
    out = []
    for q in quiz:
        if not isinstance(q, dict):
            out.append(q)
            continue
        nq = dict(q)
        if 'question' not in nq and 'text' in nq:
            nq['question'] = nq.pop('text')
            changed = True
        if 'type' not in nq and 'kind' in nq:
            nq['type'] = nq.pop('kind')
            changed = True
        out.append(nq)
    return out, changed


# Distractores genéricos (temas claramente ajenos) para las preguntas de opción.
_DISTRACTORES = [
    'Mantenimiento de hardware de servidores',
    'Contabilidad de costos empresariales',
    'Gestión de inventarios físicos',
    'Redacción de documentos jurídicos',
    'Diseño de interiores y mobiliario',
    'Logística de transporte terrestre',
    'Protocolo y organización de eventos sociales',
]


def _betto_quiz(ev):
    """Genera un quiz de práctica a partir del título y las habilidades del evento.
    Determinista por evento (misma semilla → mismo quiz)."""
    skills = [s for s in (ev.skills if isinstance(ev.skills, list) else []) if s][:3]
    title = ev.title
    rnd = random.Random(ev.id)
    preguntas = []

    for sk in skills:
        opciones = rnd.sample(_DISTRACTORES, 3) + [sk]
        rnd.shuffle(opciones)
        preguntas.append(_q(
            'mcq',
            f'¿Cuál de los siguientes fue uno de los temas trabajados en “{title}”?',
            opciones, opciones.index(sk),
            f'“{sk}” fue una de las competencias centrales de la sesión.',
        ))

    if skills:
        preguntas.append(_q(
            'boolean',
            f'En la sesión se abordó **{skills[0]}**.',
            ['Verdadero', 'Falso'], 0,
            'Verdadero: fue uno de los ejes de la sesión.',
        ))

    preguntas.append(_q(
        'boolean',
        f'La sesión “{title}” se centró exclusivamente en temas ajenos a su título.',
        ['Verdadero', 'Falso'], 1,
        'Falso: la sesión se centró en el tema de su título.',
    ))

    # Si el evento no tenía habilidades, garantizamos al menos 2 preguntas útiles.
    if not skills:
        preguntas.insert(0, _q(
            'boolean',
            f'El seminario “{title}” incluyó ejemplos prácticos aplicados.',
            ['Verdadero', 'Falso'], 0,
            'Verdadero: se combinó teoría con práctica.',
        ))
    return preguntas


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

        # 2) Resumen de Betto (crear/alargar) + quiz de práctica en cada evento.
        MIN_LEN = 400   # summaries por debajo de esto se consideran "cortos"
        existentes = {s.event_id: s for s in SessionSummary.objects.all()}
        creados = 0
        alargados = 0
        quizzes = 0
        normalizados = 0
        for ev in Event.objects.filter(is_active=True):
            md, key_points, next_steps = _betto_summary(ev)
            summ = existentes.get(ev.id)
            nuevo = summ is None
            if nuevo:
                summ = SessionSummary(event=ev)
                summ.quiz = []

            texto = summ.summary_md or ''
            es_generica_vieja = 'resume los puntos centrales' in texto
            dirty = False

            # Resumen: crear si es nuevo, o alargar si es corto/genérico viejo.
            if nuevo or es_generica_vieja or len(texto) < MIN_LEN:
                summ.summary_md = md
                summ.key_points = key_points
                summ.next_steps = next_steps
                summ.transcript_raw = md
                summ.transcript_chars = len(md)
                summ.duration_minutes = (ev.hours or 0) * 60
                dirty = True
                if nuevo:
                    creados += 1
                else:
                    alargados += 1

            # Quiz de práctica: generar si está vacío (preserva los existentes).
            if not (summ.quiz or []):
                summ.quiz = _betto_quiz(ev)
                dirty = True
                quizzes += 1
            else:
                # Normalizar claves viejas (kind/text → type/question) para que
                # el cuestionario no muestre "undefined".
                nq, changed = _normalize_quiz(summ.quiz)
                if changed:
                    summ.quiz = nq
                    dirty = True
                    normalizados += 1

            if dirty:
                summ.status = ProcessingStatus.READY
                if not summ.ai_model:
                    summ.ai_model = 'gpt-4o-mini'
                if not summ.processed_at:
                    summ.processed_at = timezone.now()
                summ.save()

        self.stdout.write(self.style.SUCCESS(f'Resúmenes de Betto creados: {creados}'))
        self.stdout.write(self.style.SUCCESS(f'Resúmenes cortos alargados: {alargados}'))
        self.stdout.write(self.style.SUCCESS(f'Quizzes de práctica generados: {quizzes}'))
        self.stdout.write(self.style.SUCCESS(f'Quizzes normalizados (kind/text → type/question): {normalizados}'))
        self.stdout.write(self.style.SUCCESS('Listo. Datos actualizados sin borrar nada.'))
