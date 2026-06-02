"""Static enums (TextChoices) — closed-vocabulary catalogs defined in code.

Use enums for closed-value fields whose meaning is part of business logic
(states, roles, modalities). For values an admin should be able to extend
without a code change, prefer a dynamic catalog model.
"""
from django.db import models


# Faculty codes (institutional proper names kept in Spanish — they are data,
# not code identifiers). The dynamic `Faculty` model mirrors these for
# admin-editable management.
FACULTY_CHOICES = [
    ('FACI', 'FACI - Ingeniería'),
    ('FACS', 'FACS - Salud'),
    ('FACE', 'FACE - Educación'),
    ('FACSECYD', 'FACSECYD - Ciencias Sociales'),
    ('POSGRADO', 'Posgrado / Otra'),
]


class AdminRole(models.TextChoices):
    SUPERADMIN = 'superadmin', 'Super administrator'
    ADMIN = 'admin', 'Administrator'


class AccessRequestStatus(models.TextChoices):
    PENDING = 'pending', 'Pending approval'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


class CertificateTemplate(models.TextChoices):
    CLASSIC = 'classic', 'Classic'
    MODERN = 'modern', 'Modern'
    GEOMETRIC = 'geometric', 'Geometric'


class EventModality(models.TextChoices):
    IN_PERSON = 'in_person', 'In person'
    VIRTUAL = 'virtual', 'Virtual'


class VirtualPlatform(models.TextChoices):
    ZOOM = 'zoom', 'Zoom'
    MEET = 'meet', 'Google Meet'
    TEAMS = 'teams', 'Microsoft Teams'
    OTHER = 'other', 'Other platform'
