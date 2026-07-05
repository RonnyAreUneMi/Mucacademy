"""Serializers públicos de certificados. Reusa los del admin."""
from api.admin.certificates.serializers import CertificadoListSerializer, CertificadoDetailSerializer

__all__ = ['CertificadoListSerializer', 'CertificadoDetailSerializer']
