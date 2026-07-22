"""Módulo de seguridad: catálogo de módulos, permisos por perfil y helpers."""
from .modules import (
    MODULES, MODULE_SLUGS, AREA_PANEL, AREA_STUDENT, ACTIONS,
    modules_by_area, module_label,
)
from .perms import role_can, user_can, participant_can, invalidate_cache

__all__ = [
    'MODULES', 'MODULE_SLUGS', 'AREA_PANEL', 'AREA_STUDENT', 'ACTIONS',
    'modules_by_area', 'module_label',
    'role_can', 'user_can', 'participant_can', 'invalidate_cache',
]
