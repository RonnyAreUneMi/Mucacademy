"""Audit log of administrative actions for legal and forensic traceability."""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class AuditAction(models.TextChoices):
    CREATE = 'CREATE', 'Create'
    UPDATE = 'UPDATE', 'Update'
    DELETE = 'DELETE', 'Delete'
    APPROVE = 'APPROVE', 'Approve'
    REJECT = 'REJECT', 'Reject'
    LOGIN = 'LOGIN', 'Login'
    LOGOUT = 'LOGOUT', 'Logout'
    DOWNLOAD = 'DOWNLOAD', 'Download'
    OTHER = 'OTHER', 'Other'


class AuditLog(models.Model):
    """Log of administrative actions."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,                          # never lose the log
        related_name='audit_logs',
    )
    action = models.CharField(
        max_length=50, choices=AuditAction.choices, db_index=True,
    )
    details = models.TextField(
        blank=True, default='',
        help_text='Human-readable description (legacy-compatible).',
    )

    # ── Audited object (polymorphic via ContentType) ─────────────
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Model type of the audited object.',
    )
    object_id = models.PositiveBigIntegerField(
        null=True, blank=True, help_text='PK of the audited object.',
    )
    target = GenericForeignKey('content_type', 'object_id')

    # ── Granular changes ─────────────────────────────────────────
    changes = models.JSONField(
        default=dict, blank=True,
        help_text='Field diff {before, after}. Empty when N/A (e.g. LOGIN).',
    )

    # ── Forensics ────────────────────────────────────────────────
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        target = f' · {self.content_type}#{self.object_id}' if self.content_type_id else ''
        return f"{self.user} - {self.action}{target} - {self.created_at:%Y-%m-%d %H:%M}"
