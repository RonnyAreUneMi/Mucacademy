"""Admin users and access requests.

`User` is the custom auth model (AbstractUser) used only by administrators.
Final participants are modeled separately in `participants.py`.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser

from core.validators import validate_ecuador_phone

from .catalogs.enums import AdminRole, AccessRequestStatus, FACULTY_CHOICES


class User(AbstractUser):
    """System user (administrators only).

    Linked to `AccessRequest`: on signup a `pending` request is created;
    a superadmin approves it to activate the user.
    """
    role = models.CharField(
        max_length=20, choices=AdminRole.choices, default=AdminRole.PROFESSOR,
        db_index=True,
    )
    faculty = models.CharField(
        max_length=20, choices=FACULTY_CHOICES, blank=True, db_index=True,
    )
    phone = models.CharField(
        max_length=20, blank=True, validators=[validate_ecuador_phone],
    )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    @property
    def full_name(self) -> str:
        """Full name, falling back to username."""
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.username

    @property
    def is_superadmin(self) -> bool:
        return self.role == AdminRole.SUPERADMIN


class AccessRequest(models.Model):
    """Access request for new administrators — requires approval.

    Invariants:
      - On rejection, `rejection_reason` must be filled.
      - `created_user` points to the User activated on approval.
    """
    first_name = models.CharField(max_length=100, verbose_name='First name')
    last_name = models.CharField(max_length=100, verbose_name='Last name')
    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=20, blank=True, validators=[validate_ecuador_phone],
    )
    faculty = models.CharField(
        max_length=20, choices=FACULTY_CHOICES, default='FACI',
        verbose_name='Faculty / Department',
    )
    status = models.CharField(
        max_length=20, choices=AccessRequestStatus.choices,
        default=AccessRequestStatus.PENDING, db_index=True,
    )
    created_user = models.OneToOneField(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='access_request',
        verbose_name='Created user',
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_requests',
        verbose_name='Approved by',
    )
    rejection_reason = models.TextField(blank=True, verbose_name='Rejection reason')

    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Access Request'
        verbose_name_plural = 'Access Requests'
        indexes = [
            models.Index(fields=['status', '-requested_at']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_status_display()}"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
