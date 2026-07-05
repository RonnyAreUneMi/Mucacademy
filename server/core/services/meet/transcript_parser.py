"""Parsea un Google Doc de transcript de Meet → texto plano.

Los transcripts de Meet tienen un formato muy regular:

    Asistentes
        Persona A, Persona B, Persona C

    Transcripción
    Persona A:  Hola buenos días, quería empezar por…
    Persona B:  Sí claro, mira lo que pasa es que…
    ...

Este módulo:
  1. Descarga el doc usando la Docs API (`documents.get`) — devuelve estructura
     JSON con `body.content` lleno de párrafos.
  2. Lo recorre extrayendo el texto crudo de cada `textRun`.
  3. Devuelve el texto concatenado, listo para mandarle a Claude.

Alternativa más simple: `drive.files().export(mimeType='text/plain')` — la
usamos como fallback si la Docs API falla por permisos.
"""
from __future__ import annotations

import io
import logging

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from .oauth import get_credentials


log = logging.getLogger(__name__)


def _docs_service():
    creds = get_credentials()
    if creds is None:
        raise RuntimeError('Sin credenciales de Google.')
    return build('docs', 'v1', credentials=creds, cache_discovery=False)


def _drive_service():
    creds = get_credentials()
    if creds is None:
        raise RuntimeError('Sin credenciales de Google.')
    return build('drive', 'v3', credentials=creds, cache_discovery=False)


def _walk_document(doc: dict) -> str:
    """Recorre el árbol del documento y concatena todo el texto."""
    chunks: list[str] = []
    body = doc.get('body', {})
    for elem in body.get('content', []):
        para = elem.get('paragraph')
        if not para:
            # Tablas, secciones, etc. — ignoramos por ahora
            continue
        line_chunks: list[str] = []
        for el in para.get('elements', []):
            tr = el.get('textRun')
            if tr and 'content' in tr:
                line_chunks.append(tr['content'])
        line = ''.join(line_chunks).rstrip('\n')
        if line.strip():
            chunks.append(line)
    return '\n'.join(chunks)


def fetch_transcript_text(file_id: str) -> str:
    """Descarga el texto plano del transcript.

    Estrategia primaria: Docs API (más limpio, separa párrafos).
    Fallback: Drive export a text/plain (si Docs API da 403).
    """
    try:
        service = _docs_service()
        doc = service.documents().get(documentId=file_id).execute()
        text = _walk_document(doc)
        if text.strip():
            return text
        log.warning('Docs API devolvió documento vacío: %s', file_id)
    except HttpError as e:
        log.warning('Docs API falló (%s), intento fallback Drive export.', e)
    except Exception as e:
        log.exception('Error inesperado en Docs API: %s', e)

    # Fallback: Drive export
    return _drive_export_plain(file_id)


def _drive_export_plain(file_id: str) -> str:
    """Fallback: usa Drive `files().export()` a text/plain."""
    service = _drive_service()
    request = service.files().export_media(
        fileId=file_id,
        mimeType='text/plain',
    )
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    raw = buf.getvalue()
    # Drive a veces devuelve UTF-8 con BOM
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
    return raw.decode('utf-8', errors='replace')


def estimate_duration_minutes(transcript: str) -> int:
    """Estima la duración del evento en minutos a partir del transcript.

    Heurística simple: cuenta palabras y asume 130 palabras/minuto (ritmo
    promedio de habla en español académico). Suficiente para un campo
    de auditoría — no hay timestamps confiables en el formato Meet.
    """
    if not transcript:
        return 0
    words = len(transcript.split())
    return max(1, round(words / 130))
