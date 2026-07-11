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
    _set_program_header_logo(batch)
    return batch


def _set_program_header_logo(batch: CertificateBatch) -> None:
    """Deja SOLO el logo UNEMI en el centro (izq/der vacíos; la derecha es CertifAI).

    Fuerza customize_design=True para que use los logos del lote (no el Diseño Global).
    """
    import os
    from django.conf import settings
    from django.core.files import File
    batch.customize_design = True
    batch.header_logo_1 = None
    batch.header_logo_3 = None
    if not batch.header_logo_2:
        path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo-unemi-removebg-preview.png')
        if os.path.exists(path):
            with open(path, 'rb') as f:
                batch.header_logo_2.save('unemi.png', File(f), save=False)
    batch.save()


# body_text excluido: los seminarios conservan su cuerpo por defecto.
DESIGN_FIELDS = (
    'customize_design', 'template',
    'color_primary', 'color_secondary', 'color_tertiary', 'color_text',
    'signatures_position',
    'signature_inst_1', 'signature_inst_2', 'signature_inst_3', 'signature_inst_4',
    'header_logo_1', 'header_logo_2', 'header_logo_3',
)


def copy_batch_design(src: CertificateBatch, dst: CertificateBatch) -> None:
    """Copia el diseño (plantilla, colores, firmas, logos) de un lote a otro."""
    for f in DESIGN_FIELDS:
        setattr(dst, f, getattr(src, f))
    dst.save()


def apply_program_design(program: Program, dst_batch: CertificateBatch) -> bool:
    """Aplica el diseño del certificado del PROGRAMA a un lote de seminario.

    El diseño vive en el lote de programa (configurado en el diseñador con
    preview). Devuelve True si se aplicó, False si el programa no tiene diseño.
    """
    program_batch = program.batches.filter(kind=CertificateKind.PROGRAM).first()
    if program_batch is None:
        return False
    copy_batch_design(program_batch, dst_batch)
    return True


def enroll_participant_in_program(program: Program, participant) -> int:
    """Inscribe al participante en TODOS los seminarios activos del programa.

    Una sola inscripción al programa → queda asociado a cada seminario.
    Idempotente (get_or_create). Devuelve cuántas inscripciones nuevas creó.
    """
    from core.models import Enrollment
    nuevas = 0
    for course in program.active_courses:
        _, created = Enrollment.objects.get_or_create(
            participant=participant, event=course, defaults={'confirmed': True},
        )
        if created:
            nuevas += 1
    return nuevas


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
    """True si aprobó la evaluación de cada seminario (acceso por inscripción, sin asistencia)."""
    return program.certificate_unlocked_for(participant)


def issue_seminar_certificate(event, participant, *, administrator=None):
    """Emite (idempotente) el certificado del seminario. Devuelve (certificate, created)."""
    from core.models import Event

    with transaction.atomic():
        ev = Event.objects.select_for_update().get(pk=event.pk)
        batch = ev.batch
        if batch is None:
            batch = CertificateBatch.objects.create(
                name=ev.title or f'Seminario {ev.date} {ev.label}',
                administrator=administrator,
                faculty=(ev.program.faculty if ev.program_id else 'FACI'),
            )
            applied = apply_program_design(ev.program, batch) if ev.program_id else False
            if not applied:
                _attach_batch_defaults(batch)
            ev.batch = batch
            ev.save(update_fields=['batch'])

        cert, created = Certificate.objects.get_or_create(
            batch=batch,
            participant=participant,
            defaults=dict(
                national_id=participant.national_id or f'GEN-{uuid.uuid4().hex[:8].upper()}',
                first_name=participant.first_name,
                last_name=participant.last_name,
                email=participant.email,
                phone=participant.phone,
                course=(ev.title or batch.name).upper(),
                course_date=ev.date,
                hours=ev.hours or 0,
            ),
        )
    if created:
        log.info('Seminar certificate issued: event=%s participant=%s', event.id, participant.id)
    return cert, created


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
