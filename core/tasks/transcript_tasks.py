"""Tareas Celery del pipeline Drive → transcript → IA → resumen.

Flujo de la task `process_event_transcript(event_id)`:

  1. Carga el evento + crea/recupera el SessionSummary vinculado.
  2. Estado=SEARCHING → busca el transcript en Drive.
     - Si no aparece todavía → estado=NO_TRANSCRIPT, sale (puede reintentarse).
  3. Estado=PROCESSING → descarga el doc, lo pasa a texto plano.
  4. Llama al pipeline IA (Claude) → resumen + cuestionario.
  5. Estado=READY → guarda todo en el modelo.

Si algo falla, deja estado=FAILED con `error_msg` para auditoría.
Ningún error de IA o Drive debe matar al worker — todo se captura.
"""
from __future__ import annotations

import logging
import traceback
from datetime import datetime

from celery import shared_task
from django.utils import timezone

from core.models import ProcessingStatus, SessionSummary, Event
from core.services.ai.transcript_summary import summarize_transcript
from core.services.meet.drive_client import find_transcript_for_session
from core.services.meet.transcript_parser import (
    estimate_duration_minutes,
    fetch_transcript_text,
)


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(),  # gestionamos errores nosotros — no auto-retry ciego
    max_retries=0,
)
def process_event_transcript(self, event_id: int) -> dict:
    """Procesa el transcript de un evento: Drive → texto → IA → DB.

    Idempotente: si ya existe un SessionSummary en estado READY, no hace nada.
    Si está FAILED o NO_TRANSCRIPT, lo reintenta desde cero.
    """
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        logger.warning('Event %s no existe', event_id)
        return {'ok': False, 'reason': 'event_no_existe', 'event_id': event_id}

    if not event.transcription_enabled:
        logger.info('Event %s tiene transcripcion deshabilitada — skip', event_id)
        return {'ok': False, 'reason': 'deshabilitada', 'event_id': event_id}

    summary, _ = SessionSummary.objects.get_or_create(event=event)

    if summary.status == ProcessingStatus.READY:
        logger.info('Event %s ya tiene resumen READY — skip', event_id)
        return {'ok': True, 'reason': 'ya_listo', 'summary_id': summary.id}

    # ── 1. Buscar en Drive ──────────────────────────────────────
    summary.status = ProcessingStatus.SEARCHING
    summary.error_msg = ''
    summary.save(update_fields=['status', 'error_msg'])

    try:
        tf = find_transcript_for_session(event)
    except Exception as e:
        logger.exception('Error buscando transcript para event %s', event_id)
        summary.status = ProcessingStatus.FAILED
        summary.error_msg = f'Drive: {e}\n{traceback.format_exc()}'
        summary.save(update_fields=['status', 'error_msg'])
        return {'ok': False, 'reason': 'drive_error', 'detail': str(e)}

    if tf is None:
        summary.status = ProcessingStatus.NO_TRANSCRIPT
        summary.save(update_fields=['status'])
        return {'ok': False, 'reason': 'sin_transcript', 'event_id': event_id}

    summary.drive_file_id = tf.file_id
    summary.drive_file_name = tf.name
    summary.save(update_fields=['drive_file_id', 'drive_file_name'])

    # ── 2. Parsear el doc → texto plano ──────────────────────────
    try:
        text = fetch_transcript_text(tf.file_id)
    except Exception as e:
        logger.exception('Error parseando transcript %s', tf.file_id)
        summary.status = ProcessingStatus.FAILED
        summary.error_msg = f'Parser: {e}\n{traceback.format_exc()}'
        summary.save(update_fields=['status', 'error_msg'])
        return {'ok': False, 'reason': 'parser_error', 'detail': str(e)}

    if not text.strip():
        summary.status = ProcessingStatus.NO_TRANSCRIPT
        summary.error_msg = 'Drive devolvió transcript vacío'
        summary.save(update_fields=['status', 'error_msg'])
        return {'ok': False, 'reason': 'transcript_vacio'}

    duracion = estimate_duration_minutes(text)
    summary.transcript_raw = text
    summary.transcript_chars = len(text)
    summary.duration_minutes = duracion
    summary.save(update_fields=[
        'transcript_raw', 'transcript_chars', 'duration_minutes',
    ])

    # ── 3. IA → resumen estructurado ─────────────────────────────
    summary.status = ProcessingStatus.PROCESSING
    summary.save(update_fields=['status'])

    try:
        result = summarize_transcript(
            text,
            titulo=event.title or '',
            fecha=str(event.date),
            duracion_minutos=duracion,
        )
    except NotImplementedError as e:
        # IA sin configurar — no es un fallo "real", deja todo en FAILED
        # con un mensaje claro para que el admin sepa qué activar.
        summary.status = ProcessingStatus.FAILED
        summary.error_msg = f'IA no configurada: {e}'
        summary.save(update_fields=['status', 'error_msg'])
        return {'ok': False, 'reason': 'ia_no_configurada', 'detail': str(e)}
    except Exception as e:
        logger.exception('Error en IA para event %s', event_id)
        summary.status = ProcessingStatus.FAILED
        summary.error_msg = f'IA: {e}\n{traceback.format_exc()}'
        summary.save(update_fields=['status', 'error_msg'])
        return {'ok': False, 'reason': 'ia_error', 'detail': str(e)}

    # ── 4. Guardar resultado ─────────────────────────────────────
    summary.summary_md = result.resumen_md
    summary.key_points = result.puntos_clave
    summary.next_steps = result.proximos_pasos
    summary.quiz = result.cuestionario
    summary.ai_model = result.ai_model
    summary.ai_input_tokens = result.ai_input_tokens
    summary.ai_output_tokens = result.ai_output_tokens
    summary.status = ProcessingStatus.READY
    summary.processed_at = timezone.now()
    summary.error_msg = ''
    summary.save()

    logger.info(
        'Resumen event %s READY (%d chars transcript → %d puntos clave, %d preguntas)',
        event_id, len(text), len(result.puntos_clave), len(result.cuestionario),
    )
    return {
        'ok': True,
        'summary_id': summary.id,
        'transcript_chars': len(text),
        'preguntas': len(result.cuestionario),
    }


@shared_task
def process_past_events() -> dict:
    """Tarea programada: revisa eventos de hoy/ayer y dispara procesamiento.

    Pensada para correr cada hora en Celery beat. Procesa eventos cuyo
    `end_time` ya pasó pero todavía no tienen resumen en estado READY.
    """
    from datetime import timedelta
    from django.db.models import Q

    ahora = timezone.now()
    desde = (ahora - timedelta(days=2)).date()
    hasta = ahora.date()

    qs = (
        Event.objects
        .filter(transcription_enabled=True)
        .filter(date__range=(desde, hasta))
        .filter(
            Q(summary__isnull=True)
            | Q(summary__status__in=[
                ProcessingStatus.PENDING,
                ProcessingStatus.NO_TRANSCRIPT,
                ProcessingStatus.FAILED,
            ])
        )
    )

    encolados = 0
    for event in qs:
        # Solo si la hora de fin ya pasó
        fin = datetime.combine(event.date, event.end_time)
        fin = timezone.make_aware(fin)
        if event.end_time < event.start_time:
            fin += timezone.timedelta(days=1)
        if fin > ahora:
            continue
        process_event_transcript.delay(event.id)
        encolados += 1

    logger.info('process_past_events: %d eventos encolados', encolados)
    return {'encoladas': encolados, 'desde': str(desde), 'hasta': str(hasta)}
