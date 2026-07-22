from django.db import migrations, models


def to_profesor(apps, schema_editor):
    apps.get_model('core', 'RolePermission').objects.filter(role='administrador').update(role='profesor')


def to_administrador(apps, schema_editor):
    apps.get_model('core', 'RolePermission').objects.filter(role='profesor').update(role='administrador')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_alter_rolepermission_role'),
    ]

    operations = [
        migrations.RunPython(to_profesor, to_administrador),
        migrations.AlterField(
            model_name='rolepermission',
            name='role',
            field=models.CharField(
                choices=[('estudiante', 'Estudiante'), ('profesor', 'Profesor')],
                db_index=True, max_length=20,
            ),
        ),
    ]
