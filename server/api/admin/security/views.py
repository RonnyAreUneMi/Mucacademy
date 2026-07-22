"""Matriz de permisos por perfil — lectura y guardado masivo. Solo superadmin."""
from rest_framework.response import Response
from rest_framework.views import APIView

from api.admin.permissions import IsSecurityAdmin
from core.base.mixins import log_audit
from core.models import AuditAction, RolePermission, SecurityRole
from core.security.modules import ACTIONS, MODULE_SLUGS, modules_by_area
from core.security.perms import invalidate_cache, role_can

ROLES = [SecurityRole.ESTUDIANTE, SecurityRole.PROFESOR]
FIELD_BY_ACTION = {
    'ver': 'can_view', 'crear': 'can_create',
    'editar': 'can_edit', 'eliminar': 'can_delete',
}


def build_matrix():
    """{role: {module: {accion: bool}}} con los valores efectivos actuales."""
    return {
        str(role): {
            slug: {a: role_can(str(role), slug, a) for a in ACTIONS}
            for slug in MODULE_SLUGS
        }
        for role in ROLES
    }


class SecurityMatrixView(APIView):
    """GET devuelve módulos + matriz; POST hace upsert masivo."""
    permission_classes = [IsSecurityAdmin]

    def get(self, request):
        areas = [
            {'area': area, 'label': label, 'modules': modules}
            for area, label, modules in modules_by_area()
        ]
        return Response({
            'actions': ACTIONS,
            'roles': [{'value': str(r), 'label': r.label} for r in ROLES],
            'areas': areas,
            'matrix': build_matrix(),
        })

    def post(self, request):
        payload = request.data.get('matrix') or {}
        valid_roles = {str(r) for r in ROLES}
        actualizados = 0

        for role, modules in payload.items():
            if role not in valid_roles or not isinstance(modules, dict):
                continue
            for module, acciones in modules.items():
                if module not in MODULE_SLUGS or not isinstance(acciones, dict):
                    continue
                defaults = {
                    field: bool(acciones.get(accion))
                    for accion, field in FIELD_BY_ACTION.items()
                }
                RolePermission.objects.update_or_create(
                    role=role, module=module, defaults=defaults,
                )
                actualizados += 1

        invalidate_cache()
        log_audit(request.user, AuditAction.UPDATE, f'Matriz de permisos actualizada ({actualizados} filas)')
        return Response({'ok': True, 'updated': actualizados, 'matrix': build_matrix()})
