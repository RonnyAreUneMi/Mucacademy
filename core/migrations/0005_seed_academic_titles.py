"""Seed the academic title catalog with the most common Ecuadorian titles."""
from django.db import migrations


SEED = [
    ('Dr.', 'Doctor', 10),
    ('Dra.', 'Doctora', 20),
    ('PhD', 'Doctor of Philosophy', 30),
    ('Mg.', 'Magíster', 40),
    ('MSc.', 'Máster en Ciencias', 50),
    ('Ing.', 'Ingeniero/a', 60),
    ('Lic.', 'Licenciado/a', 70),
    ('Ab.', 'Abogado/a', 80),
    ('Econ.', 'Economista', 90),
    ('Arq.', 'Arquitecto/a', 100),
    ('Psic.', 'Psicólogo/a', 110),
    ('Tlgo.', 'Tecnólogo/a', 120),
]


def seed_titles(apps, schema_editor):
    AcademicTitle = apps.get_model('core', 'AcademicTitle')
    for abbreviation, name, sort_order in SEED:
        AcademicTitle.objects.get_or_create(
            abbreviation=abbreviation,
            defaults={'name': name, 'sort_order': sort_order, 'is_active': True},
        )


def unseed_titles(apps, schema_editor):
    AcademicTitle = apps.get_model('core', 'AcademicTitle')
    AcademicTitle.objects.filter(
        abbreviation__in=[abbr for abbr, _, _ in SEED]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_academictitle'),
    ]

    operations = [
        migrations.RunPython(seed_titles, unseed_titles),
    ]
