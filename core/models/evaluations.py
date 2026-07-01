"""Evaluation module: graded exams with a question bank and a gradebook.

An `Evaluation` belongs to EITHER a `Program` (one exam for the whole program)
or a standalone `Event` (a seminar's own exam) — exactly one of the two.

Flow:
  - Admin builds a `Question` bank (AI-suggested + manual).
  - A participant takes the exam → `EvaluationAttempt` records their answers,
    score and pass/fail.
  - `max_attempts` bounds the tries; an admin can grant extra tries per student
    via `EvaluationGrant`.
"""
from django.core.exceptions import ValidationError
from django.db import models

from core.base.models import TimestampedModel


class QuestionKind(models.TextChoices):
    MCQ = 'mcq', 'Opción múltiple'
    BOOLEAN = 'boolean', 'Verdadero / Falso'


class QuestionSource(models.TextChoices):
    AI = 'ai', 'Generada por IA'
    MANUAL = 'manual', 'Manual'


class Evaluation(TimestampedModel):
    """A graded exam attached to a program or a single seminar."""
    program = models.OneToOneField(
        'core.Program', on_delete=models.CASCADE, related_name='evaluation',
        null=True, blank=True,
    )
    event = models.OneToOneField(
        'core.Event', on_delete=models.CASCADE, related_name='evaluation',
        null=True, blank=True,
    )
    title = models.CharField(max_length=200, default='Evaluación final')
    description = models.TextField(blank=True, default='')
    pass_threshold = models.PositiveSmallIntegerField(
        default=70, verbose_name='Nota mínima para aprobar (%)',
    )
    max_attempts = models.PositiveSmallIntegerField(
        default=2, verbose_name='Intentos permitidos',
    )
    questions_per_attempt = models.PositiveSmallIntegerField(
        default=0, verbose_name='Preguntas por intento',
        help_text='0 = usar todas las preguntas del banco.',
    )
    shuffle_questions = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Evaluation'
        verbose_name_plural = 'Evaluations'
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(program__isnull=False, event__isnull=True)
                    | models.Q(program__isnull=True, event__isnull=False)
                ),
                name='evaluation_owner_exactly_one',
            ),
        ]

    def __str__(self):
        return f'{self.title} · {self.owner_label}'

    def clean(self):
        if bool(self.program_id) == bool(self.event_id):
            raise ValidationError('La evaluación debe pertenecer a un programa O a un seminario (uno solo).')

    @property
    def owner(self):
        return self.program or self.event

    @property
    def owner_label(self) -> str:
        if self.program_id:
            return self.program.name
        if self.event_id:
            return self.event.title or self.event.day_of_week
        return '(sin dueño)'

    @property
    def active_questions(self):
        return self.questions.filter(is_active=True).order_by('order', 'id')

    @property
    def question_count(self) -> int:
        return self.active_questions.count()

    @property
    def draw_size(self) -> int:
        """Cuántas preguntas se presentan por intento."""
        total = self.question_count
        if self.questions_per_attempt and self.questions_per_attempt < total:
            return self.questions_per_attempt
        return total

    def extra_attempts_for(self, participant) -> int:
        grant = self.grants.filter(participant=participant).first()
        return grant.extra_attempts if grant else 0

    def attempts_allowed_for(self, participant) -> int:
        return self.max_attempts + self.extra_attempts_for(participant)

    def attempts_used_by(self, participant) -> int:
        return self.attempts.filter(participant=participant, submitted_at__isnull=False).count()

    def can_attempt(self, participant) -> bool:
        return self.attempts_used_by(participant) < self.attempts_allowed_for(participant)

    def best_attempt_for(self, participant):
        return (
            self.attempts.filter(participant=participant, submitted_at__isnull=False)
            .order_by('-score').first()
        )

    def passed_by(self, participant) -> bool:
        best = self.best_attempt_for(participant)
        return bool(best and best.passed)


class Question(TimestampedModel):
    """A question in an evaluation's bank."""
    evaluation = models.ForeignKey(
        Evaluation, on_delete=models.CASCADE, related_name='questions',
    )
    text = models.TextField(verbose_name='Enunciado')
    kind = models.CharField(
        max_length=10, choices=QuestionKind.choices, default=QuestionKind.MCQ,
    )
    options = models.JSONField(default=list, help_text='Lista de opciones (2 para V/F, 4 para opción múltiple).')
    correct_idx = models.PositiveSmallIntegerField(default=0)
    explanation = models.TextField(blank=True, default='')
    points = models.PositiveSmallIntegerField(default=1)
    source = models.CharField(
        max_length=10, choices=QuestionSource.choices, default=QuestionSource.MANUAL,
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'
        ordering = ['order', 'id']

    def __str__(self):
        return (self.text or '')[:60]

    @property
    def correct_option(self) -> str:
        opts = self.options or []
        if 0 <= self.correct_idx < len(opts):
            return opts[self.correct_idx]
        return ''


class EvaluationAttempt(TimestampedModel):
    """A participant's single attempt at an evaluation."""
    evaluation = models.ForeignKey(
        Evaluation, on_delete=models.CASCADE, related_name='attempts',
    )
    participant = models.ForeignKey(
        'core.Participant', on_delete=models.CASCADE, related_name='evaluation_attempts',
    )
    attempt_number = models.PositiveSmallIntegerField(default=1)
    # {question_id (str): chosen_idx (int)}
    answers = models.JSONField(default=dict)
    # Snapshot of the question ids presented (for reproducibility).
    question_ids = models.JSONField(default=list)
    correct = models.PositiveSmallIntegerField(default=0)
    total = models.PositiveSmallIntegerField(default=0)
    score = models.FloatField(default=0.0, help_text='Porcentaje 0-100.')
    passed = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Evaluation Attempt'
        verbose_name_plural = 'Evaluation Attempts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['evaluation', 'participant']),
        ]

    def __str__(self):
        return f'{self.participant} · {self.score:.0f}% ({"aprobó" if self.passed else "reprobó"})'


class EvaluationGrant(TimestampedModel):
    """Extra attempts granted to a participant beyond `max_attempts`."""
    evaluation = models.ForeignKey(
        Evaluation, on_delete=models.CASCADE, related_name='grants',
    )
    participant = models.ForeignKey(
        'core.Participant', on_delete=models.CASCADE, related_name='evaluation_grants',
    )
    extra_attempts = models.PositiveSmallIntegerField(default=1)
    reason = models.CharField(max_length=255, blank=True, default='')
    granted_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Evaluation Grant'
        verbose_name_plural = 'Evaluation Grants'
        constraints = [
            models.UniqueConstraint(
                fields=['evaluation', 'participant'], name='unique_grant_per_participant',
            ),
        ]

    def __str__(self):
        return f'+{self.extra_attempts} intentos · {self.participant}'
