"""Generación de un banco de preguntas para una evaluación mediante IA.

Para una evaluación de PROGRAMA, junta el resumen de todos sus seminarios;
para una de SEMINARIO, usa el resumen de ese evento. Con eso pide a la IA un
conjunto de preguntas (opción múltiple + verdadero/falso) para el banco.
"""
from __future__ import annotations

import json
import logging
import re

from .client import call_ai, get_runtime

log = logging.getLogger(__name__)

_SYSTEM = (
    "Eres un evaluador académico. A partir del material de un curso/programa, "
    "generas preguntas de evaluación que midan comprensión real (no trivias). "
    "Respondes SOLO con un arreglo JSON, sin texto adicional ni ```."
)

_SHAPE = """
Cada pregunta es un objeto:
- Opción múltiple: {"kind":"mcq","text":"…","options":["a","b","c","d"],"correct_idx":0,"explanation":"…"}  (4 opciones)
- Verdadero/Falso: {"kind":"boolean","text":"afirmación","options":["Verdadero","Falso"],"correct_idx":0,"explanation":"…"}
Reglas:
- Mezcla mcq y boolean (al menos 2 boolean).
- Varía la posición de la respuesta correcta.
- Cada pregunta con "explanation" breve.
- Devuelve EXACTAMENTE un arreglo JSON con {n} preguntas.
"""


def _collect_material(evaluation) -> str:
    """Junta el material de resumen de los seminarios asociados a la evaluación."""
    events = []
    if evaluation.program_id:
        events = list(evaluation.program.active_courses)
    elif evaluation.event_id:
        events = [evaluation.event]

    parts = []
    for ev in events:
        summary = getattr(ev, 'summary', None)
        title = ev.title or ev.day_of_week
        chunk = [f'### Seminario: {title}']
        if summary is not None and getattr(summary, 'resumen_md', ''):
            chunk.append(summary.resumen_md[:2500])
        elif ev.description:
            chunk.append(re.sub(r'<[^>]+>', ' ', ev.description)[:1500])
        puntos = getattr(summary, 'puntos_clave', None) or [] if summary else []
        if puntos:
            chunk.append('Puntos clave: ' + '; '.join(str(p) for p in puntos[:8]))
        parts.append('\n'.join(chunk))
    return '\n\n'.join(parts)


def _extract_list(raw: str) -> list[dict]:
    raw = raw.strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[-1]
        if raw.endswith('```'):
            raw = raw[:-3]
    for candidate in (raw, (re.search(r'\[.*\]', raw, re.DOTALL) or type('', (), {'group': lambda *_: ''})()).group(0)):
        try:
            data = json.loads(candidate)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, TypeError):
            continue
    return []


def _normalize(items: list[dict]) -> list[dict]:
    """Valida y limpia las preguntas devueltas por la IA."""
    out = []
    for q in items:
        if not isinstance(q, dict):
            continue
        text = (q.get('text') or '').strip()
        options = q.get('options') or []
        if not text or not isinstance(options, list) or len(options) not in (2, 4):
            continue
        try:
            ci = int(q.get('correct_idx', 0))
        except (TypeError, ValueError):
            ci = 0
        if not 0 <= ci < len(options):
            ci = 0
        kind = 'boolean' if len(options) == 2 else 'mcq'
        out.append({
            'text': text,
            'kind': kind,
            'options': [str(o) for o in options],
            'correct_idx': ci,
            'explanation': (q.get('explanation') or '').strip(),
        })
    return out


def generate_questions(evaluation, count: int = 10) -> list[dict]:
    """Devuelve una lista de dicts de preguntas listos para crear `Question`.

    Lanza NotImplementedError si la IA no está configurada.
    """
    if get_runtime() is None:
        raise NotImplementedError('IA no configurada.')

    material = _collect_material(evaluation)
    if not material.strip():
        material = f'Programa/seminario: {evaluation.owner_label}. (Sin resumen disponible; genera preguntas conceptuales generales del tema.)'

    from .prompts import get_prompt
    # No usamos .format(): _SHAPE tiene ejemplos JSON con llaves ({"kind":...})
    # que .format interpretaría como campos → KeyError. Sustituimos {n} a mano.
    system = get_prompt('questions') + _SHAPE.replace('{n}', str(count))
    user = f'Material:\n\n{material[:12000]}\n\nGenera el arreglo JSON de {count} preguntas.'
    raw = call_ai(system, user)
    questions = _normalize(_extract_list(raw))[:count]
    log.info('Banco IA: %d preguntas para evaluación %s', len(questions), getattr(evaluation, 'id', '?'))
    return questions
