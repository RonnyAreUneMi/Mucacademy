"""Fase 9: Mapeo inteligente de columnas Excel — PLACEHOLDER."""
from .client import is_configured


def map_excel_columns(sample_data: dict) -> dict:
    if not is_configured():
        return {
            'implemented': False,
            'message': 'Feature pendiente (Fase 9). Configura ANTHROPIC_API_KEY para habilitar.',
        }
    # TODO Fase 9
    return {'implemented': False, 'mapping': {}, 'confidence': 0.0}
