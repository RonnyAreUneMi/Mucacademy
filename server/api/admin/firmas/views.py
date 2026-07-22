from rest_framework import serializers, permissions
from api.admin.permissions import HasModulePermission

from core.models import Signature
from api.common.viewsets import AuditedModelViewSet


class FirmaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signature
        fields = ['id', 'name', 'role', 'image', 'is_active', 'sort_order', 'created_at']
        read_only_fields = ('created_at',)


class FirmaViewSet(AuditedModelViewSet):
    queryset = Signature.objects.all()
    serializer_class = FirmaSerializer
    permission_classes = [HasModulePermission]
    module_slug = 'firmas'
    search_fields = ['name', 'role']
    ordering_fields = ['sort_order', 'name']
    ordering = ['sort_order', 'name']

    audit_verbose_name = 'firma institucional'

    def audit_detail(self, instance, action):
        return f'Firma #{instance.pk} ({instance.name} - {instance.role})'
