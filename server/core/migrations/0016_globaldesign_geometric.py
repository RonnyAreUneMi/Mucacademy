"""Pone el Diseño Global (singleton) en geométrico si sigue en el default previo.

El diseño por defecto pasó a 'geometric'. Actualizamos la config global
existente solo si estaba en 'classic' (para no pisar una elección manual).
"""
from django.db import migrations


def to_geometric(apps, schema_editor):
    GlobalDesign = apps.get_model('core', 'GlobalDesign')
    GlobalDesign.objects.filter(template='classic').update(template='geometric')


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0015_alter_certificatebatch_template_and_more'),
    ]
    operations = [
        migrations.RunPython(to_geometric, noop),
    ]
