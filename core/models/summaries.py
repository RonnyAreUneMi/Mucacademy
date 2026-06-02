"""AI summary pipeline results (Drive → transcript → summary) and quiz attempts."""
from __future__ import annotations

from django.db import models


class ProcessingStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'                 # created, not queued
    SEARCHING = 'searching', 'Searching transcript' # scanning Drive
    PROCESSING = 'processing', 'Processing with AI'  # calling the LLM
    READY = 'ready', 'Ready'                        # summary available
    NO_TRANSCRIPT = 'no_transcript', 'No transcript' # Meet produced none
    FAILED = 'failed', 'Failed'                     # fatal error


class SessionSummary(models.Model):
    """AI summary of an event, generated from the Meet transcript.

    Pipeline:
      1. `drive_client` finds the transcript in the event's Drive folder.
      2. `transcript_parser` extracts plain text.
      3. `ai/transcript_summary` calls the LLM for summary + Q&A.
      4. Result is stored here.

    1-to-1 with `Event` (related_name='summary') to allow reprocessing without
    touching the main event model.
    """
    event = models.OneToOneField(
        'core.Event', on_delete=models.CASCADE, related_name='summary',
    )

    # ── Transcript source ────────────────────────────────────────
    drive_file_id = models.CharField(
        max_length=200, blank=True, default='', db_index=True,
        help_text='Transcript document ID in Google Drive.',
    )
    drive_file_name = models.CharField(
        max_length=300, blank=True, default='',
        help_text='Transcript file name in Drive (reference).',
    )
    transcript_raw = models.TextField(
        blank=True, default='',
        help_text='Plain-text transcript (parsed, unformatted).',
    )
    transcript_chars = models.IntegerField(
        default=0, help_text='Transcript character count (for audit).',
    )

    # ── AI result ────────────────────────────────────────────────
    summary_md = models.TextField(
        blank=True, default='',
        help_text='Executive summary in Markdown (key points + decisions).',
    )
    key_points = models.JSONField(
        default=list, blank=True,
        help_text='List of strings: event bullet points.',
    )
    next_steps = models.JSONField(
        default=list, blank=True,
        help_text='List of strings: recommended post-event actions.',
    )
    quiz = models.JSONField(
        default=list, blank=True,
        help_text=(
            'Review questions. Format: '
            '[{question, options: [...], correct_idx, explanation}]'
        ),
    )
    duration_minutes = models.IntegerField(
        default=0,
        help_text='Estimated event duration (from transcript length).',
    )

    # ── Status and audit ─────────────────────────────────────────
    status = models.CharField(
        max_length=20, choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING, db_index=True,
    )
    error_msg = models.TextField(
        blank=True, default='', help_text='Stack trace if status=failed.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    # AI model used (for cross-version audit)
    ai_model = models.CharField(max_length=80, blank=True, default='')
    ai_input_tokens = models.IntegerField(default=0)
    ai_output_tokens = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'AI session summary'
        verbose_name_plural = 'AI session summaries'
        ordering = ['-created_at']

    def __str__(self):
        return f'Summary #{self.id} · event {self.event_id} · {self.status}'

    @property
    def is_ready(self) -> bool:
        return self.status == ProcessingStatus.READY

    @property
    def has_failed(self) -> bool:
        return self.status in (ProcessingStatus.FAILED, ProcessingStatus.NO_TRANSCRIPT)


class QuizAttempt(models.Model):
    """A participant's attempt at the AI quiz of an event.

    Rules:
      - Each participant can have up to `MAX_ATTEMPTS` per event.
      - Score is stored on completion (all questions answered or timed out).
    """
    MAX_ATTEMPTS = 2

    participant = models.ForeignKey(
        'core.Participant', on_delete=models.CASCADE,
        related_name='quiz_attempts',
    )
    event = models.ForeignKey(
        'core.Event', on_delete=models.CASCADE,
        related_name='quiz_attempts',
    )
    correct = models.PositiveSmallIntegerField()
    total = models.PositiveSmallIntegerField()
    total_time_seconds = models.PositiveIntegerField(default=0)
    answers = models.JSONField(
        default=list, blank=True,
        help_text='List of chosen indices (null = unanswered).',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Quiz attempt'
        verbose_name_plural = 'Quiz attempts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['participant', 'event']),
        ]

    def __str__(self):
        return f'Attempt #{self.id} · event {self.event_id} · {self.correct}/{self.total}'

    @property
    def percentage(self) -> int:
        if not self.total:
            return 0
        return round(self.correct / self.total * 100)
