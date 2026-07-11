"""Restaura el cuerpo por defecto en lotes de seminario que quedaron con texto de programa."""
from django.core.management.base import BaseCommand

from core.models import CertificateBatch
from core.models.catalogs.enums import CertificateKind


class Command(BaseCommand):
    help = 'Restaura el cuerpo por defecto de los lotes de seminario que tienen texto de programa.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo reporta, no escribe.')

    def handle(self, *args, **options):
        dry = options['dry_run']
        default_body = CertificateBatch._meta.get_field('body_text').default

        afectados = [
            b for b in CertificateBatch.objects.filter(kind=CertificateKind.COURSE)
            if '{programa}' in (b.body_text or '') or '{horas}' in (b.body_text or '')
        ]

        if not afectados:
            self.stdout.write(self.style.SUCCESS('No hay lotes de seminario que reparar.'))
            return

        for b in afectados:
            self.stdout.write(f'  Lote #{b.id} "{b.name}" -> cuerpo por defecto')
            if not dry:
                b.body_text = default_body
                b.save(update_fields=['body_text'])

        verb = 'Se repararian' if dry else 'Se repararon'
        self.stdout.write(self.style.SUCCESS(f'{verb} {len(afectados)} lote(s) de seminario.'))
