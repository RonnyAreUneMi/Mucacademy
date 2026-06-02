"""Tareas Celery para envío masivo de correos transaccionales.

El uso típico es disparar `send_certificate_issued_bulk.delay(batch_id)` cuando
se genera un lote — la response del request al admin no espera el envío de
N correos vía Gmail API.

En desarrollo sin Redis, `CELERY_TASK_ALWAYS_EAGER=True` hace que la task
corra inmediatamente sincrónica (mismo comportamiento que antes).
"""
from __future__ import annotations

import logging

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from core.models import Certificate, CertificateBatch, Participant
from core.services.email import sender as email_sender

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def send_certificate_issued_bulk(self, batch_id: int) -> dict:
    """Envía notificación de certificado emitido a TODOS los certs del lote.

    Returns:
        dict con `sent`, `failed`, `total`, `batch_id`.
    """
    try:
        batch = CertificateBatch.objects.get(pk=batch_id)
    except CertificateBatch.DoesNotExist:
        logger.warning('Batch %s no existe — task abortada', batch_id)
        return {'sent': 0, 'failed': 0, 'total': 0, 'batch_id': batch_id, 'error': 'batch_not_found'}

    event = getattr(batch, 'event', None) or batch.events.first() if hasattr(batch, 'events') else None
    if event is None:
        # Caso fallback: el lote no tiene evento asociado (lote subido manualmente).
        # No mandamos correos porque no tenemos contexto del evento.
        logger.info('Batch %s no tiene evento asociado — sin envío de correos', batch_id)
        return {'sent': 0, 'failed': 0, 'total': 0, 'batch_id': batch_id, 'error': 'no_event'}

    certs = list(
        Certificate.objects
            .filter(batch=batch)
            .select_related('participant')
    )
    sent = 0
    failed = 0
    try:
        for cert in certs:
            ok = email_sender.send_certificate_issued(
                certificado=cert,
                sesion=event,
                participante=cert.participant,
                request=None,  # sin request, los URLs usan SITE_URL del settings
            )
            if ok:
                sent += 1
            else:
                failed += 1
    except SoftTimeLimitExceeded:
        logger.warning('Soft time limit alcanzado en batch %s · sent=%s failed=%s', batch_id, sent, failed)
        # Devolvemos parcial — los certs ya enviados no se reenvían en retry
        return {'sent': sent, 'failed': failed, 'total': len(certs), 'batch_id': batch_id, 'partial': True}

    logger.info('Bulk email batch %s · sent=%s failed=%s total=%s', batch_id, sent, failed, len(certs))
    return {'sent': sent, 'failed': failed, 'total': len(certs), 'batch_id': batch_id}


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def send_welcome_email_async(participant_id: int) -> bool:
    p = Participant.objects.get(pk=participant_id)
    return email_sender.send_welcome_email(p)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def send_event_inscription_async(participant_id: int, event_id: int) -> bool:
    from core.models import Event
    p = Participant.objects.get(pk=participant_id)
    s = Event.objects.get(pk=event_id)
    return email_sender.send_event_inscription(p, s)
