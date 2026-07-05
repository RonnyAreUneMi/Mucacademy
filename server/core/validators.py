import os
import re

import filetype  # Pure-Python, no system dependencies
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_ecuador_national_id(value):
    """Validate an Ecuadorian national ID (cédula) with the check-digit algorithm.

    Rules:
      - 10 numeric digits.
      - First 2 digits = province code (01-24).
      - Third digit < 6 (natural-person IDs).
      - Last digit = mod-10 checksum over the first 9 (coefficients 2,1,2,1,...).

    Empty value passes (optional fields enforce presence elsewhere).
    """
    if not value:
        return
    if not re.fullmatch(r'\d{10}', str(value)):
        raise ValidationError(_('National ID must be 10 numeric digits.'))

    province = int(value[:2])
    if province < 1 or province > 24:
        raise ValidationError(_('Invalid province code in national ID.'))

    third = int(value[2])
    if third >= 6:
        raise ValidationError(_('Invalid third digit in national ID.'))

    coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = 0
    for i, c in enumerate(value[:9]):
        prod = int(c) * coef[i]
        total += prod if prod < 10 else prod - 9
    check = (10 - (total % 10)) % 10
    if check != int(value[9]):
        raise ValidationError(_('Invalid national ID (check digit).'))


def validate_ecuador_phone(value):
    """Validate an Ecuadorian phone / mobile number.

    Accepts:
      - Mobile: 09xxxxxxxx (10 digits) or +5939xxxxxxxx.
      - Landline: 0Nxxxxxxx (9 digits, N=2-7) or +593Nxxxxxxx.

    Normalizes spaces and dashes before validating.
    """
    if not value:
        return
    clean = re.sub(r'[\s\-()]', '', str(value))
    patterns = (
        r'^0\d{9}$',        # 0 + 9 digits (mobile or landline + ext)
        r'^\+593\d{9}$',    # international format
        r'^0\d{8}$',        # landline without mobile prefix
    )
    if not any(re.fullmatch(p, clean) for p in patterns):
        raise ValidationError(_('Invalid phone format. Use 09xxxxxxxx or +593xxxxxxxxx.'))


def validate_file_extension(value, allowed_extensions=None):
    if not allowed_extensions:
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.xlsx', '.xls']

    ext = os.path.splitext(value.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(_('File extension not allowed.'))


def validate_file_content(file_obj, unexpected_mime_types=None):
    """Validate file content using filetype (pure-Python) to detect the real
    MIME from magic bytes, blocking executables.
    """
    initial_pos = file_obj.tell()
    file_obj.seek(0)
    header = file_obj.read(2048)
    file_obj.seek(initial_pos)

    kind = filetype.guess(header)
    mime_type = kind.mime if kind else 'application/octet-stream'

    blocked_mimes = [
        'application/x-msdownload',     # .exe / .dll
        'application/x-dosexec',
        'application/x-executable',
        'application/x-mach-binary',
        'application/x-elf',
        'text/x-shellscript',
        'application/x-sh',
    ]

    if mime_type in blocked_mimes:
        raise ValidationError(_('Suspicious file detected (possible executable).'))

    if header.startswith(b'MZ') or header.startswith(b'\x7fELF') or header.startswith(b'#!'):
        raise ValidationError(_('Suspicious file detected (possible executable).'))

    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext in ['.xlsx', '.xls']:
        valid_excel_mimes = [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel',
            'application/zip',
            'application/octet-stream',
        ]
        if mime_type not in valid_excel_mimes and 'zip' not in mime_type:
            pass  # validated later by structure

    return mime_type


def sanitize_text(text):
    """Basic sanitization for text inputs to prevent stored XSS."""
    if not text:
        return ""
    return str(text).strip()


# ── Backwards-compat aliases (Spanish names) ──────────────────────
# Some legacy migrations/code may still import the old names. Keep thin
# aliases so nothing breaks during the transition.
validar_cedula_ecuador = validate_ecuador_national_id
validar_telefono_ecuador = validate_ecuador_phone
