"""Resolución de permisos por perfil/módulo/acción.

Reglas:
    · `superadmin` siempre tiene acceso total (nunca se bloquea).
    · Si existe fila `RolePermission` para (perfil, módulo) manda esa fila.
    · Si NO existe, se cae al comportamiento actual del sistema
      (`core.security.modules.default_flags`), de modo que una base sin
      semilla se comporta igual que hoy y nadie queda bloqueado.
"""
import time

from django.db.utils import OperationalError, ProgrammingError

from .modules import ACTIONS, default_flags

# TTL corto: acota la desincronización entre workers cuando se guarda la matriz.
_CACHE_TTL = 10
_CACHE = None
_CACHE_AT = 0.0


def invalidate_cache():
    global _CACHE
    _CACHE = None


def _matrix():
    """{(role, module): (ver, crear, editar, eliminar)} cacheado en memoria."""
    global _CACHE, _CACHE_AT
    now = time.monotonic()
    if _CACHE is not None and (now - _CACHE_AT) < _CACHE_TTL:
        return _CACHE
    try:
        from core.models.security import RolePermission
        rows = RolePermission.objects.all().values_list(
            'role', 'module', 'can_view', 'can_create', 'can_edit', 'can_delete',
        )
        _CACHE = {(r[0], r[1]): (r[2], r[3], r[4], r[5]) for r in rows}
        _CACHE_AT = now
    except (OperationalError, ProgrammingError):
        return {}
    return _CACHE


def _profile_for_user_role(user_role: str):
    """Perfil configurable a partir de `User.role`. None si no aplica."""
    from core.models.security import USER_ROLE_TO_PROFILE
    return USER_ROLE_TO_PROFILE.get(user_role)


def role_can(role: str, module: str, action: str = 'ver') -> bool:
    """¿El perfil `role` puede ejecutar `action` sobre `module`?"""
    if role == 'superadmin':
        return True
    if action not in ACTIONS:
        return False
    idx = ACTIONS.index(action)
    flags = _matrix().get((role, module))
    if flags is None:
        flags = default_flags(role, module)
    return bool(flags[idx])


def user_can(user, module: str, action: str = 'ver') -> bool:
    """Permiso de un `User` del panel. Superadmin siempre True."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    user_role = getattr(user, 'role', None)
    if user_role == 'superadmin' or getattr(user, 'is_superuser', False):
        return True
    profile = _profile_for_user_role(user_role)
    if profile is None:
        return False
    return role_can(str(profile), module, action)


def participant_can(module: str, action: str = 'ver') -> bool:
    """Permiso del perfil `estudiante` (Participant del área pública)."""
    return role_can('estudiante', module, action)
