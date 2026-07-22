from django.db import migrations


def drop_profesor(apps, schema_editor):
    apps.get_model('core', 'RolePermission').objects.filter(role='profesor').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_seed_role_permissions'),
    ]

    operations = [
        migrations.RunPython(drop_profesor, migrations.RunPython.noop),
    ]
