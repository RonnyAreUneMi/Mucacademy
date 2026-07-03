"""Program-certificate issuance.

A participant earns the program certificate automatically once they hold the
individual certificate of *every* active course in the program. Issuance is
idempotent: a participant gets at most one program certificate per program.
"""
from __future__ import annotations

import logging
import uuid

from django.db import transaction

from core.models import Attendance, Certificate, CertificateBatch, Program, Signature
from core.models.catalogs.enums import CertificateKind

log = logging.getLogger(__name__)

DEFAULT_PROGRAM_BODY = (
    "Por haber culminado satisfactoriamente el programa '{programa}', "
    "completando la totalidad de sus cursos con un total de {horas} horas "
    "académicas y desarrollando las competencias detalladas a continuación."
)


def _attach_batch_defaults(batch: CertificateBatch) -> None:
    """Populate a fresh batch with the default signatures (sin logos hardcodeados)."""
    firmas = list(Signature.objects.filter(is_active=True).order_by('sort_order')[:3])
    for i, firma in enumerate(firmas, start=1):
        setattr(batch, f'signature_inst_{i}', firma)
    # Los logos salen del Diseño Global / config del lote, no hardcodeados.
    batch.save()


def get_or_create_program_batch(program: Program, administrator=None) -> CertificateBatch:
    """Return the single program-certificate batch for this program, creating it once."""
    batch = program.batches.filter(kind=CertificateKind.PROGRAM).first()
    if batch:
        return batch

    batch = CertificateBatch(
        name=program.name,
        administrator=administrator,
        faculty=program.faculty,
        kind=CertificateKind.PROGRAM,
        program=program,
        body_text=program.certificate_body or DEFAULT_PROGRAM_BODY,
    )
    batch.save()
    _attach_batch_defaults(batch)
    return batch


def participant_attended_all(program: Program, participant) -> bool:
    """True if the participant has an attendance record for EVERY active seminar."""
    courses = list(program.active_courses)
    if not courses:
        return False
    for course in courses:
        if not Attendance.objects.filter(event=course, participant=participant).exists():
            return False
    return True


def participant_completed_program(program: Program, participant) -> bool:
    """True if the participant may receive the program certificate.

    Requisitos (decisión del proyecto): asistió a TODOS los seminarios y,
    si el programa tiene una evaluación activa, la aprobó.
    """
    if not participant_attended_all(program, participant):
        return False
    evaluation = getattr(program, 'evaluation', None)
    if evaluation is not None and evaluation.is_active:
        return evaluation.passed_by(participant)
    return True


def issue_program_certificate(program: Program, participant, *, administrator=None):
    """Idempotently issue the program certificate. Returns (certificate, created)."""
    with transaction.atomic():
        batch = get_or_create_program_batch(program, administrator)
        existing = Certificate.objects.filter(batch=batch, participant=participant).first()
        if existing:
            return existing, False

        snapshot = program.courses_snapshot()
        total_hours = sum(c['hours'] for c in snapshot)

        cert = Certificate.objects.create(
            batch=batch,
            participant=participant,
            national_id=participant.national_id or f'GEN-{uuid.uuid4().hex[:8].upper()}',
            first_name=participant.first_name,
            last_name=participant.last_name,
            email=participant.email,
            phone=participant.phone,
            course=program.name.upper(),
            hours=total_hours,
            program_data=snapshot,
        )
    log.info('Program certificate issued: program=%s participant=%s', program.id, participant.id)
    return cert, True


def check_and_issue(program: Program, participant, *, administrator=None):
    """Issue the program cert if the participant just completed all courses.

    Returns the newly-created Certificate, or None if not eligible / already had it.
    """
    if program is None or not program.is_active:
        return None
    if participant is None:
        return None
    if not participant_completed_program(program, participant):
        return None
    cert, created = issue_program_certificate(program, participant, administrator=administrator)
    return cert if created else None
