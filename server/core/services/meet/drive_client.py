"""Cliente de Google Drive para localizar transcripts de Meet.

Google Meet guarda los transcripts automáticamente en el Drive del organizador
del evento, dentro de la carpeta `Meet Recordings/` (subcarpeta nombrada según
el nombre del evento).

Formato típico de un archivo de transcript:
    "{Nombre del evento} - Transcripción {YYYY/MM/DD HH:MM} GMT-XX"
    mimeType: application/vnd.google-apps.document   (Google Doc)

Pipeline:
  1. `find_transcript_for_session(sesion)` — busca el doc más cercano por fecha
     y título.
  2. Devuelve `{file_id, name, web_link}` o None si todavía no apareció.
  3. `transcript_parser` se encarga después de exportarlo a texto plano.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .oauth import get_credentials


log = logging.getLogger(__name__)


# Google Docs mimeType (los transcripts de Meet siempre son docs)
MIME_GOOGLE_DOC = 'application/vnd.google-apps.document'

# Palabras que aparecen en el nombre del archivo de transcript de Meet,
# en distintos idiomas (Meet usa el locale del organizador).
TRANSCRIPT_KEYWORDS = (
    'Transcripción',     # es-ES (con tilde)
    'Transcripcion',     # es-ES (sin tilde, fallback)
    'Transcript',        # en
    'Transcrição',       # pt-BR
    'Transcription',     # fr
)


@dataclass(slots=True)
class TranscriptFile:
    """Resultado de la búsqueda en Drive."""
    file_id: str
    name: str
    web_link: str
    created_time: datetime | None
    matched_keyword: str  # qué keyword del título lo identificó


def _drive_service():
    """Construye el cliente Drive v3 con las credenciales del singleton."""
    creds = get_credentials()
    if creds is None:
        raise RuntimeError(
            'No hay credenciales de Google guardadas. '
            'Conecta una cuenta en /admin → Google → Conectar.'
        )
    return build('drive', 'v3', credentials=creds, cache_discovery=False)


def _build_query(after: datetime, before: datetime) -> str:
    """Construye la query de Drive: docs creados en el rango, no en papelera."""
    after_iso = after.strftime('%Y-%m-%dT%H:%M:%S')
    before_iso = before.strftime('%Y-%m-%dT%H:%M:%S')
    return (
        f"mimeType = '{MIME_GOOGLE_DOC}' "
        f"and trashed = false "
        f"and createdTime >= '{after_iso}' "
        f"and createdTime <= '{before_iso}'"
    )


def _list_candidate_docs(after: datetime, before: datetime) -> list[dict]:
    """Lista todos los Google Docs creados en una ventana de tiempo."""
    service = _drive_service()
    query = _build_query(after, before)

    try:
        resp = service.files().list(
            q=query,
            pageSize=100,
            orderBy='createdTime desc',
            fields='files(id, name, createdTime, webViewLink)',
            spaces='drive',
            corpora='user',
            supportsAllDrives=False,
        ).execute()
    except HttpError as e:
        log.exception('Error consultando Drive: %s', e)
        raise

    return resp.get('files', [])


def _is_transcript(name: str) -> str | None:
    """Si el nombre contiene alguna keyword de transcript, devuelve cuál."""
    for kw in TRANSCRIPT_KEYWORDS:
        if kw.lower() in name.lower():
            return kw
    return None


def _title_matches(file_name: str, sesion_titulo: str) -> bool:
    """Heurística laxa: ¿el nombre del archivo contiene el título de la sesión?

    Meet usa el "summary" del evento de Calendar como prefijo del transcript,
    así que `sesion.titulo` debería aparecer literal o casi literal.
    """
    if not sesion_titulo:
        return True  # sin título → aceptamos cualquier transcript del rango
    needle = sesion_titulo.strip().lower()
    haystack = file_name.lower()
    # Match exacto o por prefijo (los primeros 20 chars del título)
    return needle in haystack or needle[:20] in haystack


def find_transcript_for_session(sesion) -> TranscriptFile | None:
    """Busca el transcript de Meet correspondiente a una sesión.

    Estrategia:
      1. Define ventana = [hora_inicio − 1h, hora_fin + 24h] (los transcripts
         tardan minutos/horas en aparecer tras terminar la reunión).
      2. Lista Google Docs creados en esa ventana en el Drive del usuario.
      3. Filtra por:
           - nombre contiene "Transcripción" / "Transcript" / etc.
           - nombre contiene el título de la sesión (heurística laxa).
      4. Devuelve el mejor candidato (el más reciente que matchee ambos).
    """
    from django.utils import timezone

    fecha_local = timezone.make_aware(
        datetime.combine(sesion.date, sesion.start_time)
    )
    fecha_fin_local = timezone.make_aware(
        datetime.combine(sesion.date, sesion.end_time)
    )
    # Si cruza medianoche, hora_fin < hora_inicio → suma un día
    if fecha_fin_local <= fecha_local:
        fecha_fin_local += timedelta(days=1)

    # Ventana amplia: 7 días hacia atrás + 24h hacia adelante. Permite que
    # eventos creados con fecha futura, pero que ya se realizaron antes,
    # encuentren su transcript (el matching final se afina por título).
    after = (fecha_local - timedelta(days=7)).astimezone()
    before = (fecha_fin_local + timedelta(hours=24)).astimezone()

    docs = _list_candidate_docs(after, before)
    log.info('Drive: %d docs creados entre %s y %s', len(docs), after, before)

    candidates: list[TranscriptFile] = []
    for d in docs:
        name = d.get('name', '')
        kw = _is_transcript(name)
        if not kw:
            continue
        if not _title_matches(name, sesion.title or ''):
            continue
        created = _parse_iso(d.get('createdTime'))
        candidates.append(TranscriptFile(
            file_id=d['id'],
            name=name,
            web_link=d.get('webViewLink', ''),
            created_time=created,
            matched_keyword=kw,
        ))

    if not candidates:
        log.info('No hay transcript todavía para sesión %s', sesion.id)
        return None

    # Best match: el más reciente (Drive ya nos los devolvió por desc)
    best = candidates[0]
    log.info(
        'Transcript encontrado para sesión %s: %s (id=%s)',
        sesion.id, best.name, best.file_id,
    )
    return best


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    # Drive devuelve tipo "2026-05-03T14:30:00.000Z"
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except ValueError:
        return None


@dataclass(slots=True)
class RecordingFile:
    """Grabación .mp4/.webm de la reunión de Meet."""
    file_id: str
    name: str
    web_link: str
    download_url: str
    created_time: datetime | None


def find_recording_for_session(sesion) -> RecordingFile | None:
    """Busca el video de la grabación de Meet en Drive.

    Misma ventana temporal que el transcript, pero filtra por mimeType de
    video. El nombre suele ser "{titulo} - {fecha} GMT-XX.mp4".
    """
    from django.utils import timezone

    fecha_local = timezone.make_aware(
        datetime.combine(sesion.date, sesion.start_time)
    )
    fecha_fin_local = timezone.make_aware(
        datetime.combine(sesion.date, sesion.end_time)
    )
    if fecha_fin_local <= fecha_local:
        fecha_fin_local += timedelta(days=1)

    # Ventana amplia (ver `find_transcript_for_session`)
    after = (fecha_local - timedelta(days=7)).astimezone()
    before = (fecha_fin_local + timedelta(hours=24)).astimezone()

    service = _drive_service()
    after_iso = after.strftime('%Y-%m-%dT%H:%M:%S')
    before_iso = before.strftime('%Y-%m-%dT%H:%M:%S')
    query = (
        f"(mimeType contains 'video/') "
        f"and trashed = false "
        f"and createdTime >= '{after_iso}' "
        f"and createdTime <= '{before_iso}'"
    )

    try:
        resp = service.files().list(
            q=query,
            pageSize=20,
            orderBy='createdTime desc',
            fields='files(id, name, createdTime, webViewLink, webContentLink)',
            spaces='drive',
            corpora='user',
            supportsAllDrives=False,
        ).execute()
    except HttpError as e:
        log.warning('Error consultando grabaciones en Drive: %s', e)
        return None

    candidates = resp.get('files', [])
    if not candidates:
        log.info('No hay grabación de video para sesión %s', sesion.id)
        return None

    # Si hay título, filtrar por nombre similar; si no, devolver el más reciente
    if sesion.title:
        needle = sesion.title.strip().lower()
        for f in candidates:
            if needle in (f.get('name') or '').lower() or needle[:20] in (f.get('name') or '').lower():
                return _build_recording(f)

    # Fallback: el más reciente
    return _build_recording(candidates[0])


def _build_recording(f: dict) -> RecordingFile:
    return RecordingFile(
        file_id=f['id'],
        name=f.get('name', ''),
        web_link=f.get('webViewLink', ''),
        download_url=f.get('webContentLink', ''),
        created_time=_parse_iso(f.get('createdTime')),
    )


def list_recent_transcripts(days: int = 7) -> list[TranscriptFile]:
    """Helper de debug: lista todos los transcripts recientes en el Drive.

    Útil para `python manage.py shell` cuando estás afinando la heurística.
    """
    from django.utils import timezone
    now = timezone.now()
    after = now - timedelta(days=days)
    docs = _list_candidate_docs(after, now)

    out: list[TranscriptFile] = []
    for d in docs:
        kw = _is_transcript(d.get('name', ''))
        if not kw:
            continue
        out.append(TranscriptFile(
            file_id=d['id'],
            name=d.get('name', ''),
            web_link=d.get('webViewLink', ''),
            created_time=_parse_iso(d.get('createdTime')),
            matched_keyword=kw,
        ))
    return out
