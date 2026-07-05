"""Sugerencia de habilidades/competencias de un curso mediante IA.

A partir del título, descripción y (si existe) el resumen del evento, propone
una lista corta de competencias concretas para imprimir en el certificado de
programa.
"""
from __future__ import annotations

import json
import logging
import re

from .client import call_ai, get_runtime

log = logging.getLogger(__name__)

_SYSTEM = (
    "Eres un diseñador instruccional. Dado un curso universitario, propones las "
    "competencias/habilidades concretas que un estudiante adquiere al completarlo. "
    "Respondes SOLO con un arreglo JSON de 3 a 6 strings cortos (máx. 8 palabras "
    "cada uno), en español, sin texto adicional ni ```."
)


def _extract_list(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[-1]
        if raw.endswith('```'):
            raw = raw[:-3]
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(s).strip() for s in data if str(s).strip()]
    except json.JSONDecodeError:
        pass
    # Fallback: extraer el primer arreglo balanceado
    m = re.search(r'\[.*\]', raw, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list):
                return [str(s).strip() for s in data if str(s).strip()]
        except json.JSONDecodeError:
            pass
    return []


def suggest_skills_for_event(event) -> list[str]:
    """Devuelve una lista de competencias sugeridas para el curso.

    Lanza NotImplementedError si la IA no está configurada.
    """
    if get_runtime() is None:
        raise NotImplementedError('IA no configurada.')

    parts = [f'Título del curso: {event.title or "(sin título)"}']
    if event.description:
        # descripción puede venir con HTML del editor: limpiamos etiquetas simples
        desc = re.sub(r'<[^>]+>', ' ', event.description)
        parts.append(f'Descripción: {desc.strip()[:1500]}')

    summary = getattr(event, 'summary', None)
    if summary is not None:
        if getattr(summary, 'resumen_md', ''):
            parts.append(f'Resumen del curso: {summary.resumen_md[:2000]}')
        puntos = getattr(summary, 'puntos_clave', None) or []
        if puntos:
            parts.append('Puntos clave: ' + '; '.join(str(p) for p in puntos[:8]))

    from .prompts import get_prompt
    user = '\n\n'.join(parts) + '\n\nDevuelve el arreglo JSON de competencias.'
    raw = call_ai(get_prompt('skills'), user)
    skills = _extract_list(raw)[:6]
    log.info('Skills sugeridas para evento %s: %s', getattr(event, 'id', '?'), skills)
    return skills
