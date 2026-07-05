"""Fase 12: Extracción de entidades desde voz — PLACEHOLDER."""
from .client import is_configured


def extract_entities_from_voice(transcripcion: str) -> dict:
    if not is_configured():
        return {
            'implemented': False,
            'message': 'Comandos de voz pendientes (Fase 12). Configura ANTHROPIC_API_KEY.',
            'entidades': {},
            'faltantes_criticos': [],
        }
    # TODO Fase 12
    return {'implemented': False, 'entidades': {}, 'faltantes_criticos': []}
