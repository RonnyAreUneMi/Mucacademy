"""Crea las filas de RolePermission faltantes con los permisos por defecto.

Idempotente: nunca pisa una fila existente, solo agrega las que faltan. Los
valores por defecto replican el comportamiento actual del sistema, así que
ejecutarlo no cambia el acceso de nadie.
"""
from django.core.management.base import BaseCommand

from core.security.modules import ACTIONS, MODULE_SLUGS, default_flags

ROLES = ['estudiante', 'profesor']

_FIELDS = ['can_view', 'can_create', 'can_edit', 'can_delete']


def seed_role_permissions(model):
    """Crea las combinaciones (perfil, módulo) que falten. Devuelve cuántas creó."""
    existing = set(model.objects.values_list('role', 'module'))
    nuevos = []
    for role in ROLES:
        for slug in MODULE_SLUGS:
            if (role, slug) in existing:
                continue
            flags = default_flags(role, slug)
            nuevos.append(model(
                role=role, module=slug,
                **{f: flags[i] for i, f in enumerate(_FIELDS)},
            ))
    if nuevos:
        model.objects.bulk_create(nuevos)
    return len(nuevos)


class Command(BaseCommand):
    help = 'Siembra los permisos por defecto de cada perfil (idempotente).'

    def handle(self, *args, **options):
        from core.models import RolePermission
        creados = seed_role_permissions(RolePermission)
        total = RolePermission.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'Permisos sembrados: {creados} nuevos, {total} filas en total '
            f'({len(ROLES)} perfiles x {len(MODULE_SLUGS)} modulos x {len(ACTIONS)} acciones).'
        ))
