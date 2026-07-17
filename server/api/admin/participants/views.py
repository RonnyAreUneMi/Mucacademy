from django.db.models import Count
from rest_framework import permissions
from api.admin.permissions import IsPanelAdmin
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import Participant
from api.common.viewsets import AuditedModelViewSet

from .serializers import (
    ParticipanteListSerializer,
    ParticipanteDetailSerializer,
    ParticipanteWriteSerializer,
    CertificadoMiniSerializer,
)


class ParticipanteViewSet(AuditedModelViewSet):
    queryset = Participant.objects.annotate(certificados_count=Count('certificates'))
    permission_classes = [IsPanelAdmin]
    filterset_fields = ['is_leader']
    search_fields = ['national_id', 'email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'first_name', 'last_name']
    ordering = ['-created_at']

    audit_verbose_name = 'participante'

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ParticipanteWriteSerializer
        if self.action == 'retrieve':
            return ParticipanteDetailSerializer
        return ParticipanteListSerializer

    def audit_detail(self, instance, action):
        return f'Participante #{instance.pk} ({instance.first_name} {instance.last_name})'

    @action(detail=True, methods=['get'])
    def certificates(self, request, pk=None):
        p = self.get_object()
        return Response(CertificadoMiniSerializer(p.certificates.all(), many=True).data)

    @action(detail=True, methods=['post'])
    def toggle_leader(self, request, pk=None):
        p = self.get_object()
        p.is_leader = not p.is_leader
        p.save(update_fields=['is_leader'])
        self.log_audit('TOGGLE_LIDER', f'Participante #{p.pk} → is_leader={p.is_leader}')
        return Response({'id': p.id, 'is_leader': p.is_leader})
