"""Siembra los permisos por defecto de cada perfil.

Los valores replican el comportamiento actual del sistema, así que aplicar
esta migración no cambia el acceso de ningún usuario.
"""
from django.db import migrations

from core.management.commands.seed_permisos import seed_role_permissions


def seed(apps, schema_editor):
    seed_role_permissions(apps.get_model('core', 'RolePermission'))


def unseed(apps, schema_editor):
    apps.get_model('core', 'RolePermission').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_rolepermission'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
