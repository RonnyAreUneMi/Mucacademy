"""Catalogs — both static enums and dynamic lookup tables.

Layout:
- `enums.py`   → TextChoices (static, defined in code)
- `faculty.py` → Faculty (admin-editable dynamic catalog)
"""
from .enums import (
    FACULTY_CHOICES,
    AdminRole,
    AccessRequestStatus,
    CertificateTemplate,
    EventModality,
    VirtualPlatform,
)
from .faculty import Faculty

__all__ = [
    'FACULTY_CHOICES',
    'AdminRole',
    'AccessRequestStatus',
    'CertificateTemplate',
    'EventModality',
    'VirtualPlatform',
    'Faculty',
]
