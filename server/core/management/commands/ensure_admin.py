"""
Garantiza un superusuario admin con contraseña conocida.

Útil en Railway: asegura que siempre exista un admin con credenciales
predecibles (configurables por variables de entorno).

Variables (opcionales):
    DJANGO_SUPERUSER_USERNAME (default: admin)
    DJANGO_SUPERUSER_PASSWORD (default: Azvcar3r0)
    DJANGO_SUPERUSER_EMAIL    (default: admin@certifai.app)
"""
import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea o actualiza el superusuario admin con una contraseña conocida."

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'certifai2026')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@certifai.app')

        user = User.objects.filter(username=username).first()
        if user is None:
            user = User(username=username, email=email)

        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        if hasattr(user, 'role'):
            user.role = 'superadmin'
        if hasattr(user, 'is_active'):
            user.is_active = True
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f"Superusuario '{username}' listo (contraseña actualizada)."
        ))
