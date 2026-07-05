"""Fase 11: Recomendaciones con embeddings — PLACEHOLDER."""
from .client import is_configured


def recommend_for_email(email: str, top_n: int = 3) -> dict:
    if not is_configured():
        return {
            'implemented': False,
            'message': 'Recomendaciones pendientes (Fase 11). Requiere pgvector + embeddings.',
            'recommendations': [],
        }
    # TODO Fase 11: cargar embeddings y calcular similaridad
    return {'implemented': False, 'recommendations': []}
