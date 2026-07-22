from rest_framework.permissions import BasePermission

from core.security.perms import user_can

# HTTP method → acción del módulo de seguridad.
METHOD_ACTIONS = {
    'GET': 'ver',
    'HEAD': 'ver',
    'OPTIONS': 'ver',
    'POST': 'crear',
    'PUT': 'editar',
    'PATCH': 'editar',
    'DELETE': 'eliminar',
}


class IsPanelAdmin(BasePermission):
    """Acceso para usuarios del panel (rol admin o superadmin), sin depender de is_staff."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated
            and getattr(user, 'role', None) in ('admin', 'superadmin')
        )


class HasModulePermission(IsPanelAdmin):
    """`IsPanelAdmin` + permiso del módulo declarado en `view.module_slug`.

    Sin `module_slug` se comporta igual que `IsPanelAdmin`. Superadmin nunca
    se bloquea.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        module = getattr(view, 'module_slug', None)
        if not module:
            return True
        action = METHOD_ACTIONS.get(request.method, 'ver')
        return user_can(request.user, module, action)


class IsSecurityAdmin(BasePermission):
    """Solo superadmin — administración de la matriz de permisos."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated
            and (getattr(user, 'role', None) == 'superadmin' or user.is_superuser)
        )
