from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import User
from core.models.catalogs.enums import AdminRole
from api.common.viewsets import AuditedModelViewSet

from .serializers import UsuarioListSerializer, UsuarioWriteSerializer, PasswordResetSerializer


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_superuser or getattr(u, 'role', '') == 'superadmin'))


class UsuarioViewSet(AuditedModelViewSet):
    """Gestión de usuarios admin. Solo superadmin."""
    queryset = User.objects.all()
    permission_classes = [IsSuperAdmin]
    filterset_fields = ['role', 'faculty', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'username']
    ordering = ['-date_joined']

    audit_verbose_name = 'usuario'

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return UsuarioWriteSerializer
        return UsuarioListSerializer

    def audit_detail(self, instance, action):
        return f'Usuario #{instance.pk} ({instance.username})'

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        user = self.get_object()
        ser = PasswordResetSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user.set_password(ser.validated_data['new_password'])
        user.save(update_fields=['password'])
        self.log_audit('RESET_PASSWORD', f'Password reseteado para {user.username}')
        return Response({'success': True, 'message': 'Contraseña actualizada'})

    @action(detail=True, methods=['post'], url_path='set-role')
    def set_role(self, request, pk=None):
        """Cambia el rol de un usuario. Superadmin = admin total; profesor = sin acceso al panel."""
        user = self.get_object()
        role = (request.data.get('role') or '').strip()
        valid = {r for r, _ in AdminRole.choices}
        if role not in valid:
            return Response({'error': 'Rol inválido.'}, status=400)
        if user.id == request.user.id:
            return Response({'error': 'No puedes cambiar tu propio rol.'}, status=400)
        # No dejar el sistema sin superadmins.
        if user.role == 'superadmin' and role != 'superadmin':
            remaining = User.objects.filter(role='superadmin').exclude(id=user.id).count()
            if remaining == 0:
                return Response({'error': 'Debe quedar al menos un superadministrador.'}, status=400)

        user.role = role
        # Alinear flags de Django: profesor NO es staff (sin acceso al panel/API admin).
        user.is_superuser = (role == 'superadmin')
        user.is_staff = (role != 'professor')
        user.save(update_fields=['role', 'is_superuser', 'is_staff'])
        self.log_audit('UPDATE', f'Rol de {user.username} → {role}')
        return Response({'ok': True, 'role': role, 'rol_display': user.get_role_display()})
