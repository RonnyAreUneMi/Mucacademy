"""
Importa los datos iniciales (fixture data.json) una sola vez.

Si la base ya tiene programas cargados, no hace nada — así no se pisan datos
agregados después. Idempotente.

Uso:
    python manage.py import_data
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from core.models import Program


class Command(BaseCommand):
    help = "Importa los datos iniciales (fixture data.json) si la base está vacía."

    def handle(self, *args, **options):
        if Program.objects.exists():
            self.stdout.write("Datos ya presentes. No se realizan cambios.")
            return

        self.stdout.write("Importando datos iniciales...")
        try:
            call_command('loaddata', 'data')
            self.stdout.write(self.style.SUCCESS("Datos importados correctamente."))
        except Exception as exc:
            # Un fallo aquí no debe tumbar el arranque de la app.
            self.stdout.write(self.style.ERROR(f"Importación falló (se continúa): {exc}"))
