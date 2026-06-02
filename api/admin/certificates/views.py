from rest_framework import permissions

from core.models import Certificate
from api.common.viewsets import AuditedModelViewSet

from .serializers import (
    CertificadoListSerializer,
    CertificadoDetailSerializer,
    CertificadoWriteSerializer,
)


class CertificadoViewSet(AuditedModelViewSet):
    """CRUD admin de certificados. La parte pública está en api/public/."""
    queryset = Certificate.objects.with_relations()
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['batch', 'participant']
    search_fields = ['national_id', 'email', 'first_name', 'last_name', 'course', 'verification_hash']
    ordering_fields = ['created_at', 'download_count']
    ordering = ['-created_at']
    lookup_field = 'verification_hash'

    audit_verbose_name = 'certificado'

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return CertificadoWriteSerializer
        if self.action == 'retrieve':
            return CertificadoDetailSerializer
        return CertificadoListSerializer

    def audit_detail(self, instance, action):
        return f'Certificado #{instance.pk} ({instance.national_id} - {instance.course})'
