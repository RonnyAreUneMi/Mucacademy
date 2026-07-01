"""Events (sessions), speakers, attendance and enrollments."""
import uuid

from django.db import models

from core.managers import EventManager

from .catalogs.enums import EventModality, VirtualPlatform


class Event(models.Model):
    """An event/session with a specific date and time for attendance.

    Invariants:
      - If `modality='virtual'`, it should have a `meeting_url` (clean()).
      - `qr_code` is unique and immutable (used in the public check-in URL).
      - Events may cross midnight (end_time < start_time) for night events.
    """
    batch = models.ForeignKey(
        'core.CertificateBatch', on_delete=models.CASCADE,
        related_name='events', verbose_name='Program',
        null=True, blank=True,
    )
    title = models.CharField(
        max_length=200, blank=True,
        help_text='Descriptive title (e.g. "Morning session - Monday")',
    )
    description = models.TextField(blank=True, default='', verbose_name='Description')
    banner_image = models.ImageField(
        upload_to='event_banners/', null=True, blank=True,
        verbose_name='Banner image',
        help_text='Promotional image shown on the registration page',
    )
    modality = models.CharField(
        max_length=15, choices=EventModality.choices, default=EventModality.IN_PERSON,
        verbose_name='Modality',
    )
    virtual_platform = models.CharField(
        max_length=15, choices=VirtualPlatform.choices, blank=True, default='',
        verbose_name='Platform',
        help_text='Only applies to virtual events',
    )
    meeting_url = models.URLField(
        max_length=500, blank=True, default='',
        verbose_name='Meeting URL',
        help_text='Zoom/Meet/Teams URL (only for virtual events)',
    )
    location = models.CharField(max_length=300, blank=True, default='', verbose_name='Location')
    date = models.DateField(verbose_name='Event date')
    start_time = models.TimeField(verbose_name='Start time')
    end_time = models.TimeField(verbose_name='End time')
    qr_code = models.CharField(
        max_length=64, unique=True, default=uuid.uuid4,
        editable=False, db_index=True,
    )
    capacity = models.PositiveIntegerField(
        default=0, verbose_name='Max capacity', help_text='0 = unlimited',
    )
    leaders_only = models.BooleanField(
        default=False, verbose_name='Academic leaders only',
        help_text='Only participants marked as leaders can register',
    )
    is_active = models.BooleanField(default=True)

    # Programa académico: un evento puede ser un curso dentro de un programa
    # (p.ej. "SQL" dentro de "Analítica de Datos"). Si es null, es un
    # curso/seminario suelto.
    program = models.ForeignKey(
        'core.Program', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='courses', verbose_name='Programa',
        help_text='Si pertenece a un programa, se agrupa bajo él.',
    )
    skills = models.JSONField(
        default=list, blank=True, verbose_name='Habilidades / competencias',
        help_text='Habilidades que desarrolla este curso (se listan en el certificado de programa).',
    )
    hours = models.PositiveIntegerField(
        default=0, verbose_name='Horas del curso',
        help_text='Horas académicas de este curso (usadas en el certificado).',
    )

    # Versionamiento / seminarios en partes
    has_parts = models.BooleanField(
        default=False, verbose_name='Seminario dividido en partes',
        help_text='Si está activo, este evento es parte de una serie (parte 1, 2, …).',
    )
    parent_event = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='parts', verbose_name='Primera parte de la serie',
        help_text='Para continuaciones: apunta al evento que es la primera parte.',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # Google Meet integration
    google_calendar_event_id = models.CharField(
        max_length=200, blank=True, default='', db_index=True,
        help_text='Google Calendar event ID (to update or delete it).',
    )
    transcription_enabled = models.BooleanField(
        default=True, verbose_name='Generate AI summary of the event',
        help_text='If on, the Meet transcript is processed with AI after the event.',
    )

    # Evaluación (quiz) y su relación con el certificado
    quiz_enabled = models.BooleanField(
        default=True, verbose_name='Generar y mostrar cuestionario',
        help_text='Si está apagado, no se genera ni se muestra el quiz del evento.',
    )
    certificate_requires_quiz = models.BooleanField(
        default=False, verbose_name='Requiere aprobar el quiz para el certificado',
        help_text='Si está activo, solo se emite certificado a quien apruebe el cuestionario.',
    )
    quiz_pass_threshold = models.PositiveSmallIntegerField(
        default=70, verbose_name='Nota mínima del quiz (%)',
        help_text='Porcentaje mínimo para aprobar el cuestionario (0-100).',
    )

    objects = EventManager()

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = 'Event'
        verbose_name_plural = 'Events'
        indexes = [
            models.Index(fields=['qr_code']),
            models.Index(fields=['date', 'is_active']),
        ]

    def __str__(self):
        return (
            f"{self.day_of_week} {self.date} "
            f"({self.start_time:%H:%M}–{self.end_time:%H:%M})"
        )

    @property
    def day_of_week(self) -> str:
        """Day of the week derived from `date` (not persisted)."""
        days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        if not self.date:
            return ''
        return days[self.date.weekday()]

    @property
    def label(self):
        return f"{self.start_time:%H:%M} – {self.end_time:%H:%M}"

    @property
    def is_series_root(self) -> bool:
        """True si es la primera parte de una serie (catálogo de series)."""
        return self.has_parts and self.parent_event_id is None

    @property
    def series_root(self):
        """Devuelve la primera parte de la serie (o sí mismo si lo es)."""
        return self.parent_event if self.parent_event_id else self

    def quiz_passed_by(self, participant) -> bool:
        """True si el participante aprobó el quiz (mejor intento ≥ umbral)."""
        if participant is None:
            return False
        best = (
            self.quiz_attempts.filter(participant=participant)
            .order_by('-correct').first()
        )
        if not best or not best.total:
            return False
        return best.percentage >= self.quiz_pass_threshold

    def certificate_unlocked_for(self, participant) -> bool:
        """True si el participante puede recibir certificado según la config de quiz."""
        if not self.certificate_requires_quiz:
            return True
        return self.quiz_passed_by(participant)

    @property
    def is_unlimited(self):
        return self.capacity == 0

    @property
    def enrolled_count(self):
        return self.enrollments.count()

    @property
    def available_seats(self):
        if self.is_unlimited:
            return None
        return max(0, self.capacity - self.enrolled_count)

    @property
    def is_full(self):
        if self.is_unlimited:
            return False
        return self.enrolled_count >= self.capacity

    @property
    def is_virtual(self):
        return self.modality == EventModality.VIRTUAL

    @property
    def platform_display_safe(self):
        if self.virtual_platform:
            return self.get_virtual_platform_display()
        return 'Virtual meeting'

    def clean(self):
        """Virtual event with platform=meet may leave the URL empty: it is
        auto-filled when the Google Calendar event is created. For other
        platforms the URL stays required.
        """
        from django.core.exceptions import ValidationError
        if self.modality == EventModality.VIRTUAL and not self.meeting_url:
            if self.virtual_platform != VirtualPlatform.MEET:
                raise ValidationError({
                    'meeting_url': 'You must provide a URL for virtual events.'
                })


class Speaker(models.Model):
    """Person who delivers an event.

    An event can have one or many speakers. Deleting the event cascades.
    `sort_order` controls appearance order on the public event page.
    """
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name='speakers',
    )
    name = models.CharField(max_length=200, verbose_name='Full name')
    title = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name='Title / Position', help_text='E.g. Dr., MSc., Eng., PhD',
    )
    affiliation = models.CharField(
        max_length=200, blank=True, default='',
        verbose_name='Affiliation / Institution',
        help_text='E.g. UNEMI, MIT, Stanford',
    )
    bio = models.TextField(blank=True, default='', verbose_name='Short bio')
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Speaker'
        verbose_name_plural = 'Speakers'

    def __str__(self):
        prefix = f'{self.title} ' if self.title else ''
        return f'{prefix}{self.name}'.strip()

    @property
    def display_name(self) -> str:
        prefix = f'{self.title} ' if self.title else ''
        suffix = f' · {self.affiliation}' if self.affiliation else ''
        return f'{prefix}{self.name}{suffix}'.strip()


class Attendance(models.Model):
    """Attendance record created when scanning the QR during the event.

    A participant cannot record attendance twice for the same event
    (unique event+participant). IP is stored for audit.
    """
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name='attendances',
    )
    certificate = models.ForeignKey(
        'core.Certificate', on_delete=models.CASCADE,
        related_name='attendances', null=True, blank=True,
    )
    participant = models.ForeignKey(
        'core.Participant', on_delete=models.CASCADE,
        related_name='attendances', null=True, blank=True,
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        ordering = ['-registered_at']
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendances'
        constraints = [
            models.UniqueConstraint(
                fields=['event', 'participant'],
                name='unique_attendance_event_participant',
            ),
        ]

    def __str__(self):
        who = self.participant.first_name if self.participant else (
            self.certificate.first_name if self.certificate else '?')
        return f"{who} → {self.event}"


class Enrollment(models.Model):
    """Pre-registration: the participant commits to attending.

    Invariants:
      - Unique per (participant, event): cannot enroll twice.
      - `blocked=True` when the participant enrolled but did not attend
        (manually flagged by admin to penalize absences).
    """
    certificate = models.ForeignKey(
        'core.Certificate', on_delete=models.CASCADE,
        related_name='enrollments', null=True, blank=True,
    )
    participant = models.ForeignKey(
        'core.Participant', on_delete=models.CASCADE,
        related_name='enrollments', null=True, blank=True,
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name='enrollments',
    )
    confirmed = models.BooleanField(default=True)
    blocked = models.BooleanField(
        default=False,
        help_text='If absent without justification, the account is blocked.',
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enrolled_at']
        verbose_name = 'Enrollment'
        verbose_name_plural = 'Enrollments'
        constraints = [
            models.UniqueConstraint(
                fields=['participant', 'event'],
                name='unique_enrollment_participant_event',
            ),
        ]

    def __str__(self):
        who = self.participant.first_name if self.participant else (
            self.certificate.first_name if self.certificate else '?')
        status = 'Blocked' if self.blocked else 'Confirmed'
        return f"{who} — {status}"
