"""
Siembra el catálogo de títulos académicos (AcademicTitle).

Idempotente: usa get_or_create por abreviado, así que puede ejecutarse
varias veces sin duplicar. Pensado para poblar el catálogo en una DB ya
migrada o para reponer entradas borradas.

Uso:
    python manage.py seed_academic_titles
    python manage.py seed_academic_titles --reset   # borra el catálogo y vuelve a sembrar
"""
from django.core.management.base import BaseCommand

from core.models import AcademicTitle


# (abreviado, nombre completo, orden)
TITLES = [
    ('Dr.',   'Doctor',                 10),
    ('Dra.',  'Doctora',                20),
    ('PhD',   'Doctor of Philosophy',   30),
    ('Mg.',   'Magíster',               40),
    ('Mgs.',  'Magíster (alt.)',        45),
    ('MSc.',  'Máster en Ciencias',     50),
    ('MBA',   'Máster en Administración de Empresas', 55),
    ('Esp.',  'Especialista',           58),
    ('Ing.',  'Ingeniero/a',            60),
    ('Lic.',  'Licenciado/a',           70),
    ('Ab.',   'Abogado/a',              80),
    ('Dr(c).','Doctorando (candidato)', 85),
    ('Econ.', 'Economista',             90),
    ('Arq.',  'Arquitecto/a',           100),
    ('Psic.', 'Psicólogo/a',            110),
    ('Tlgo.', 'Tecnólogo/a',            120),
    ('CPA',   'Contador Público Autorizado', 130),
    ('Od.',   'Odontólogo/a',           140),
    ('Md.',   'Médico/a',               150),
    ('Q.F.',  'Químico/a Farmacéutico/a', 160),
    ('Sr.',   'Señor',                  900),
    ('Sra.',  'Señora',                 910),
]


class Command(BaseCommand):
    help = "Siembra el catálogo de títulos académicos (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Borra todas las entradas del catálogo antes de sembrar.',
        )

    def handle(self, *args, **options):
        if options['reset']:
            deleted, _ = AcademicTitle.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f'Catálogo reseteado: {deleted} entradas eliminadas.'
            ))

        created = 0
        updated = 0
        for abbreviation, name, sort_order in TITLES:
            obj, was_created = AcademicTitle.objects.get_or_create(
                abbreviation=abbreviation,
                defaults={'name': name, 'sort_order': sort_order, 'is_active': True},
            )
            if was_created:
                created += 1
            else:
                # Mantiene el nombre/orden alineados con la semilla sin tocar is_active.
                changed = False
                if obj.name != name:
                    obj.name = name
                    changed = True
                if obj.sort_order != sort_order:
                    obj.sort_order = sort_order
                    changed = True
                if changed:
                    obj.save(update_fields=['name', 'sort_order'])
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Títulos académicos sembrados: {created} nuevos, {updated} actualizados, '
            f'{AcademicTitle.objects.count()} en total.'
        ))
