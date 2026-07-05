"""Seed the Faculty catalog with the five UNEMI faculties."""
from django.db import migrations


FACULTIES = [
    ('FACI', 'FACI - Ingeniería', 1),
    ('FACS', 'FACS - Salud', 2),
    ('FACE', 'FACE - Educación', 3),
    ('FACSECYD', 'FACSECYD - Ciencias Sociales', 4),
    ('POSGRADO', 'Posgrado / Otra', 5),
]


def seed(apps, schema_editor):
    Faculty = apps.get_model('core', 'Faculty')
    for code, name, order in FACULTIES:
        Faculty.objects.get_or_create(
            code=code,
            defaults={'name': name, 'sort_order': order, 'is_active': True},
        )


def unseed(apps, schema_editor):
    Faculty = apps.get_model('core', 'Faculty')
    Faculty.objects.filter(code__in=[c for c, _, _ in FACULTIES]).delete()


class Migration(migrations.Migration):
    dependencies = [('core', '0001_initial')]
    operations = [migrations.RunPython(seed, unseed)]
