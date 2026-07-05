"""Agrega 'Comunidad Universitaria' al catálogo dinámico Faculty (transversal)."""
from django.db import migrations


def add_comunidad(apps, schema_editor):
    Faculty = apps.get_model('core', 'Faculty')
    Faculty.objects.get_or_create(
        code='COMUNIDAD',
        defaults={
            'name': 'Comunidad Universitaria',
            'description': 'Opción transversal: aplica a toda la comunidad, no a una facultad específica.',
            'sort_order': 90,
            'is_active': True,
        },
    )


def remove_comunidad(apps, schema_editor):
    Faculty = apps.get_model('core', 'Faculty')
    Faculty.objects.filter(code='COMUNIDAD').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_alter_accessrequest_faculty_and_more'),
    ]

    operations = [
        migrations.RunPython(add_comunidad, remove_comunidad),
    ]
