"""Permisos por perfil y módulo — matriz editable desde el panel de Seguridad.

El perfil `superadmin` no se almacena aquí: siempre tiene acceso total.
"""
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.security.modules import MODULE_SLUGS, module_label


class SecurityRole(models.TextChoices):
    ESTUDIANTE = 'estudiante', 'Estudiante'
    PROFESOR = 'profesor', 'Profesor'
    ADMINISTRADOR = 'administrador', 'Administrador'


# User.role (AdminRole) → perfil configurable de seguridad.
USER_ROLE_TO_PROFILE = {
    'admin': SecurityRole.ADMINISTRADOR,
    'professor': SecurityRole.PROFESOR,
}


class RolePermission(models.Model):
    """Permisos de un perfil sobre un módulo del sistema."""

    role = models.CharField(max_length=20, choices=SecurityRole.choices, db_index=True)
    module = models.CharField(max_length=40, db_index=True)
    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'permiso de perfil'
        verbose_name_plural = 'permisos de perfiles'
        unique_together = ('role', 'module')
        ordering = ['role', 'module']

    def __str__(self):
        acciones = ''.join([
            'V' if self.can_view else '-',
            'C' if self.can_create else '-',
            'E' if self.can_edit else '-',
            'D' if self.can_delete else '-',
        ])
        return f'{self.get_role_display()} · {module_label(self.module)} [{acciones}]'

    @property
    def is_known_module(self) -> bool:
        return self.module in MODULE_SLUGS

    def flags(self):
        return (self.can_view, self.can_create, self.can_edit, self.can_delete)


@receiver(post_save, sender=RolePermission)
@receiver(post_delete, sender=RolePermission)
def _invalidate_permission_cache(sender, **kwargs):
    from core.security.perms import invalidate_cache
    invalidate_cache()
