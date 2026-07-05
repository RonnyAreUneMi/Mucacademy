from rest_framework import serializers, permissions

from core.models import AuditLog
from api.common.viewsets import AuditedReadOnlyModelViewSet


class AuditoriaSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='user.username', read_only=True)
    usuario_nombre = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'usuario_username', 'usuario_nombre', 'action', 'details', 'created_at']
        read_only_fields = fields

    def get_usuario_nombre(self, obj):
        u = obj.user
        return f'{u.first_name} {u.last_name}'.strip() if u else ''


class AuditoriaViewSet(AuditedReadOnlyModelViewSet):
    """Logs de auditoría (solo lectura, solo staff)."""
    queryset = AuditLog.objects.select_related('user')
    serializer_class = AuditoriaSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['action', 'user']
    search_fields = ['action', 'details', 'user__username']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
