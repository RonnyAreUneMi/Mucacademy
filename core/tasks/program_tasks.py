"""Celery tasks for automatic program-certificate issuance.

After a course batch is generated, we check every participant of that course:
those who now hold the certificate of *every* course in the program earn the
program certificate automatically (and get notified by email).
"""
from __future__ import annotations

import logging

from celery import shared_task

from core.models import Certificate, Event
from core.services import programs as program_service
from core.services.email import sender as email_sender

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def issue_program_certificates_for_event(event_id: int) -> dict:
    """For the event's program, issue program certs to whoever just completed it.

    Iterates the participants that hold a certificate in this course's batch,
    and for each one checks whether they've now completed the whole program.
    """
    try:
        event = Event.objects.select_related('program').get(pk=event_id)
    except Event.DoesNotExist:
        return {'issued': 0, 'error': 'event_not_found', 'event_id': event_id}

    program = event.program
    if program is None or not program.is_active:
        return {'issued': 0, 'reason': 'no_active_program', 'event_id': event_id}
    if event.batch_id is None:
        return {'issued': 0, 'reason': 'course_has_no_batch', 'event_id': event_id}

    # Candidates: participants who just earned this course's certificate.
    candidates = (
        Certificate.objects
        .filter(batch_id=event.batch_id, participant__isnull=False)
        .select_related('participant')
    )

    issued = 0
    emailed = 0
    for cert in candidates:
        participant = cert.participant
        new_cert = program_service.check_and_issue(program, participant)
        if new_cert is None:
            continue
        issued += 1
        try:
            ok = email_sender.send_program_certificate_issued(
                certificado=new_cert, program=program, participante=participant, request=None,
            )
            emailed += int(bool(ok))
        except Exception:  # email must never block issuance
            logger.exception('Failed to email program cert to participant %s', participant.id)

    logger.info(
        'Program issuance for event %s (program %s): issued=%s emailed=%s',
        event_id, program.id, issued, emailed,
    )
    return {'issued': issued, 'emailed': emailed, 'program_id': program.id, 'event_id': event_id}
