"""Academic programs: an umbrella that groups several courses (events).

A `Program` (e.g. "Analítica de Datos") contains several course-events
(SQL, Excel, Power BI). Each course is issued its own certificate, and once
a participant holds the certificate of *every* course of the program, a
program-level certificate is issued automatically — listing each course and
the skills it covered.
"""
from django.db import models

from core.base.models import TimestampedModel

from .catalogs.enums import FACULTY_CHOICES, CertificateTemplate


class Program(TimestampedModel):
    """Umbrella grouping several course-events under a single certification.

    Courses are `Event` rows with `event.program == self` (related_name
    `courses`). The program certificate is emitted automatically when a
    participant completes every active course of the program.
    """
    name = models.CharField(max_length=200, verbose_name='Program name')
    description = models.TextField(blank=True, default='', verbose_name='Description')
    banner_image = models.ImageField(
        upload_to='program_banners/', null=True, blank=True,
        verbose_name='Banner image',
        help_text='Imagen promocional del programa (puede generarse con IA).',
    )
    faculty = models.CharField(
        max_length=20, choices=FACULTY_CHOICES, default='FACI', db_index=True,
    )
    is_active = models.BooleanField(default=True)
    is_open = models.BooleanField(
        default=False, verbose_name='Programa publicado',
        help_text='Si está apagado, el programa está en configuración y los participantes no lo ven.',
    )

    # Custom body for the program certificate. `{programa}` and `{horas}` are
    # replaced at render time. Left blank → a sensible default is used.
    certificate_body = models.TextField(
        blank=True, default='',
        verbose_name='Program certificate body',
        help_text=(
            "Texto del certificado de programa. Usa {programa} y {horas} como "
            "variables. Si se deja vacío se usa un texto por defecto."
        ),
    )

    # Diseño y firmas compartidos por TODOS los seminarios del programa
    # (y por el certificado del programa). El seminario suelto es independiente.
    template = models.CharField(
        max_length=20, choices=CertificateTemplate.choices, default=CertificateTemplate.CLASSIC,
        verbose_name='Plantilla del certificado',
    )
    signature_inst_1 = models.ForeignKey(
        'core.Signature', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='programs_slot1', verbose_name='Firma 1',
    )
    signature_inst_2 = models.ForeignKey(
        'core.Signature', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='programs_slot2', verbose_name='Firma 2',
    )
    signature_inst_3 = models.ForeignKey(
        'core.Signature', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='programs_slot3', verbose_name='Firma 3',
    )

    class Meta:
        verbose_name = 'Program'
        verbose_name_plural = 'Programs'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'name']),
            models.Index(fields=['faculty']),
        ]

    def __str__(self):
        return self.name

    @property
    def active_courses(self):
        """Active course-events that make up this program, in schedule order."""
        return self.courses.filter(is_active=True).order_by('date', 'start_time')

    @property
    def course_count(self) -> int:
        return self.active_courses.count()

    @property
    def total_hours(self) -> int:
        """Sum of the declared hours of every active course."""
        return sum(c.hours or 0 for c in self.active_courses)

    def certificate_unlocked_for(self, participant) -> bool:
        """True si el participante aprobó la evaluación de TODOS los seminarios.

        Regla: el certificado del programa se obtiene aprobando el test de cada
        seminario. Un seminario sin evaluación no bloquea (se da por cumplido).
        """
        if participant is None:
            return False
        for course in self.active_courses:
            evaluation = getattr(course, 'evaluation', None)
            if evaluation is None or not evaluation.is_active:
                continue  # seminario sin test → no bloquea
            if not evaluation.passed_by(participant):
                return False
        return True

    def pending_evaluations_for(self, participant) -> list:
        """Seminarios cuya evaluación aún no ha aprobado el participante."""
        pending = []
        for course in self.active_courses:
            evaluation = getattr(course, 'evaluation', None)
            if evaluation and evaluation.is_active and not evaluation.passed_by(participant):
                pending.append(course)
        return pending

    def courses_snapshot(self) -> list[dict]:
        """Frozen structure printed on the program certificate.

        Returns a list of ``{name, hours, skills}`` — one per active course.
        """
        snapshot = []
        for course in self.active_courses:
            snapshot.append({
                'name': course.title or course.day_of_week,
                'hours': course.hours or 0,
                'skills': list(course.skills or []),
            })
        return snapshot
