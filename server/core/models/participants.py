"""Participants (final users) and their API auth tokens."""
import hashlib
import secrets
import uuid
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.base.models import TimestampedModel
from core.managers import ParticipantManager
from core.validators import validate_ecuador_national_id, validate_ecuador_phone


class Participant(TimestampedModel):
    """A unique participant / student in the system.

    Invariants:
      - Must have at least `national_id` OR `email` (validated in clean()).
      - `national_id` unique when non-empty; `email` unique when non-empty.

    Optional auth:
      - `password_hash` is set only if the participant creates a public account.
      - Guest flow (event signup by national ID without account) still works:
        with no password there is no login, only lookup.
    """
    national_id = models.CharField(
        max_length=20, blank=True, default='', db_index=True,
        validators=[validate_ecuador_national_id],
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=200, db_index=True)
    phone = models.CharField(
        max_length=20, blank=True, default='',
        validators=[validate_ecuador_phone],
    )
    is_leader = models.BooleanField(
        default=False, verbose_name='Academic leader', db_index=True,
    )

    # ── Public auth (optional) ──────────────────────────────────
    password_hash = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Django PBKDF2 hash. Empty = guest (no account).',
    )
    last_login = models.DateTimeField(null=True, blank=True)
    avatar = models.ImageField(
        upload_to='participants/avatars/', null=True, blank=True,
        help_text='Profile photo (optional).',
    )

    objects = ParticipantManager()

    class Meta:
        verbose_name = 'Participant'
        verbose_name_plural = 'Participants'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['national_id'],
                name='unique_national_id_when_not_empty',
                condition=~models.Q(national_id=''),
            ),
            models.UniqueConstraint(
                fields=['email'],
                name='unique_email_when_not_empty',
                condition=~models.Q(email=''),
            ),
        ]
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['national_id']),
        ]

    def clean(self):
        if not self.national_id and not self.email:
            raise ValidationError('You must provide at least a national ID or email.')

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.national_id or self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def has_account(self) -> bool:
        return bool(self.password_hash)

    @property
    def initials(self) -> str:
        n = (self.first_name or '').strip()
        a = (self.last_name or '').strip()
        return ((n[:1] + a[:1]) or 'P').upper()

    # ── Auth helpers ────────────────────────────────────────────
    def set_password(self, raw_password: str) -> None:
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password(raw_password, self.password_hash)


class ParticipantToken(TimestampedModel):
    """Bearer token for mobile app / API clients.

    Each mobile login creates a new token, sent as `Authorization: Token <key>`.
    """
    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name='tokens',
    )
    key = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        verbose_name = 'Participant token'
        verbose_name_plural = 'Participant tokens'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['expires_at'])]

    def __str__(self):
        return f'Token<{self.participant_id}, …{self.key[-6:]}>'

    @classmethod
    def generate_for(cls, participant: 'Participant', *, days: int = 30, user_agent: str = '') -> 'ParticipantToken':
        return cls.objects.create(
            participant=participant,
            key=secrets.token_urlsafe(40),
            expires_at=timezone.now() + timedelta(days=days),
            user_agent=user_agent[:255],
        )

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at


class PasswordResetToken(TimestampedModel):
    """Short-lived token for password recovery.

    A single request creates one row containing:
      - `token`  : URL-safe UUID used for the magic link (clickable from email).
      - `code_hash` : SHA-256 of a 6-digit code for cross-device entry.
      - `expires_at` : 15 minutes from creation.
      - `used_at` : null until consumed (single-use guarantee).

    Either the magic link OR the code can verify the request — whichever wins
    first marks the token as used, invalidating the other path.
    """
    TOKEN_TTL = timedelta(minutes=15)

    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name='password_reset_tokens',
    )
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    code_hash = models.CharField(max_length=64, help_text='SHA-256 of the 6-digit code.')
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    requested_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        verbose_name = 'Password reset token'
        verbose_name_plural = 'Password reset tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token', 'used_at']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f'PasswordReset<{self.participant_id}, {"used" if self.used_at else "active"}>'

    # ── Factory ─────────────────────────────────────────────────
    @classmethod
    def issue(cls, participant: Participant, *, ip: str = '', user_agent: str = '') -> tuple['PasswordResetToken', str]:
        """Create a new token. Returns (instance, plaintext_code).

        Invalidates any previous active tokens for the same participant so
        only the latest request can succeed.
        """
        cls.objects.filter(
            participant=participant, used_at__isnull=True, expires_at__gt=timezone.now(),
        ).update(used_at=timezone.now())

        code = f'{secrets.randbelow(1_000_000):06d}'
        instance = cls.objects.create(
            participant=participant,
            code_hash=cls._hash_code(code),
            expires_at=timezone.now() + cls.TOKEN_TTL,
            requested_ip=ip or None,
            user_agent=user_agent[:255],
        )
        return instance, code

    @staticmethod
    def _hash_code(code: str) -> str:
        return hashlib.sha256(code.strip().encode('utf-8')).hexdigest()

    # ── Validation ──────────────────────────────────────────────
    @property
    def is_active(self) -> bool:
        return self.used_at is None and timezone.now() < self.expires_at

    def matches_code(self, code: str) -> bool:
        """Constant-time comparison against the stored hash."""
        if not self.is_active or not code:
            return False
        return secrets.compare_digest(self.code_hash, self._hash_code(code))

    def consume(self) -> None:
        """Mark as used (single-use enforcement)."""
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])
