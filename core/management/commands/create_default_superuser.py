"""
Crea un superusuario por defecto si no existe.
Pensado para ejecutarse automáticamente en el primer despliegue (Railway).

Uso:
    python manage.py create_default_superuser

Variables de entorno opcionales (para sobreescribir los valores por defecto):
    DJANGO_SUPERUSER_USERNAME (default: admin)
    DJANGO_SUPERUSER_EMAIL    (default: admin@certify.local)
    DJANGO_SUPERUSER_PASSWORD (default: Azvcar3r0)
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Crea un superusuario por defecto si no existe ninguno con ese username."

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@certify.local')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'Azvcar3r0')

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(
                f"El superusuario '{username}' ya existe. No se realizan cambios."
            ))
            return

        extra = {}
        # Si el modelo User tiene campo 'role', asignar superadmin
        if hasattr(User, 'role'):
            extra['role'] = 'superadmin'
        if hasattr(User, 'is_active'):
            extra['is_active'] = True

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            **extra,
        )

        self.stdout.write(self.style.SUCCESS(
            f"Superusuario '{username}' creado correctamente."
        ))
