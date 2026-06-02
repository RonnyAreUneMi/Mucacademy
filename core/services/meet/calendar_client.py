"""Cliente Google Calendar — crear / actualizar / eliminar eventos con Meet.

Toda función devuelve None silenciosamente si no hay credencial conectada.
Esto permite seguir creando sesiones virtuales aunque OAuth no esté listo
(el admin podrá pegar el link Meet manual como fallback).

Convenciones:
- Una sola cuenta (UNEMI) organiza todos los eventos → no recibimos `email`
  como parámetro, lo lee de la credencial guardada.
- Timezone: si la sesión no especifica una, usamos `settings.TIME_ZONE`.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING

from django.conf import settings
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .oauth import get_credentials

if TYPE_CHECKING:
    from core.models import Event

logger = logging.getLogger(__name__)


def _build_service():
    """Construye el cliente Calendar API. None si no hay credenciales."""
    creds = get_credentials()
    if creds is None:
        return None
    return build('calendar', 'v3', credentials=creds, cache_discovery=False)


def _datetime_for(date, hora: time) -> str:
    """Combina date + time en RFC3339 sin offset (Calendar usa el timeZone aparte)."""
    return datetime.combine(date, hora).isoformat()


def _event_body(sesion: 'Event', include_meet: bool = True) -> dict:
    """Construye el dict que pide events.insert/patch."""
    tz = getattr(settings, 'TIME_ZONE', 'America/Guayaquil')
    summary = sesion.title or f'Sesión {sesion.day_of_week} {sesion.date}'
    body: dict = {
        'summary': summary,
        'description': sesion.description or '',
        'start': {
            'dateTime': _datetime_for(sesion.date, sesion.start_time),
            'timeZone': tz,
        },
        'end': {
            'dateTime': _datetime_for(sesion.date, sesion.end_time),
            'timeZone': tz,
        },
    }
    if sesion.location:
        body['location'] = sesion.location
    if include_meet:
        body['conferenceData'] = {
            'createRequest': {
                'requestId': uuid.uuid4().hex,
                'conferenceSolutionKey': {'type': 'hangoutsMeet'},
            },
        }
    return body


def create_meet_event(sesion: 'Event') -> tuple[str, str] | None:
    """Crea un evento en Calendar con link Meet adjunto.

    Devuelve (meet_link, event_id) si funciona, None si:
      - No hay credenciales conectadas (OAuth pendiente).
      - Calendar API rechaza la request (loggeamos warning).
    """
    service = _build_service()
    if service is None:
        logger.info('create_meet_event: sin credenciales Google, skip')
        return None

    try:
        event = (
            service.events()
            .insert(
                calendarId='primary',
                body=_event_body(sesion, include_meet=True),
                conferenceDataVersion=1,
            )
            .execute()
        )
    except HttpError as exc:
        logger.warning('create_meet_event falló: %s', exc)
        return None

    meet_link = ''
    for ep in event.get('conferenceData', {}).get('entryPoints', []):
        if ep.get('entryPointType') == 'video':
            meet_link = ep.get('uri', '')
            break
    if not meet_link:
        meet_link = event.get('hangoutLink', '')

    return meet_link, event['id']


def update_meet_event(sesion: 'Event') -> bool:
    """Actualiza fecha/hora/título de un evento existente. True si OK."""
    if not sesion.google_calendar_event_id:
        return False
    service = _build_service()
    if service is None:
        return False
    try:
        service.events().patch(
            calendarId='primary',
            eventId=sesion.google_calendar_event_id,
            body=_event_body(sesion, include_meet=False),
        ).execute()
        return True
    except HttpError as exc:
        logger.warning('update_meet_event #%s falló: %s', sesion.pk, exc)
        return False


def delete_meet_event(event_id: str) -> bool:
    """Borra el evento de Calendar (cancela la reunión)."""
    if not event_id:
        return False
    service = _build_service()
    if service is None:
        return False
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return True
    except HttpError as exc:
        logger.warning('delete_meet_event %s falló: %s', event_id, exc)
        return False
