"""Serializers públicos de sesiones. Reusa los de admin (son apropiados para lectura)."""
from api.admin.sessions.serializers import SesionListSerializer, SesionDetailSerializer

__all__ = ['SesionListSerializer', 'SesionDetailSerializer']
