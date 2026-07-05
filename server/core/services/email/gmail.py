"""Envío de correos vía Gmail API usando el OAuth de la cuenta institucional.

Usa las credenciales guardadas en `GoogleCredential` (singleton). Requiere
que el scope `gmail.send` haya sido autorizado en `/panel/google/connect/`.

Uso simple:
    from core.services.email.gmail import send_email
    send_email(
        to='alguien@ejemplo.com',
        subject='Hola',
        html='<h1>Bienvenido</h1>',
        text='Bienvenido',  # fallback opcional
    )

Para envíos masivos / con logging robusto, usar `send_email_message(EmailMessage)`
que es lo que llama el Django EmailBackend custom.
"""
from __future__ import annotations

import base64
import logging
from email.message import EmailMessage as PyEmailMessage
from email.utils import make_msgid

from django.conf import settings
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.services.meet import oauth as goauth

logger = logging.getLogger(__name__)


class GmailNotConfigured(Exception):
    """No hay credenciales Google guardadas o falta el scope gmail.send."""


def _build_service():
    creds = goauth.get_credentials()
    if creds is None:
        raise GmailNotConfigured(
            'No hay cuenta Google conectada. Conecta una en /panel/google/connect/.'
        )
    if 'https://www.googleapis.com/auth/gmail.send' not in (creds.scopes or []):
        raise GmailNotConfigured(
            'Faltan permisos de Gmail. Re-autoriza en /panel/google/connect/ '
            'para conceder el scope gmail.send.'
        )
    return build('gmail', 'v1', credentials=creds, cache_discovery=False)


def _build_mime(*, sender: str, to: list[str], subject: str,
                html: str | None, text: str | None,
                cc: list[str] | None = None,
                bcc: list[str] | None = None,
                reply_to: str | None = None,
                attachments: list[tuple[str, bytes, str]] | None = None) -> PyEmailMessage:
    """Construye un MIME multipart/alternative o multipart/mixed."""
    msg = PyEmailMessage()
    msg['From'] = sender
    msg['To'] = ', '.join(to)
    if cc:
        msg['Cc'] = ', '.join(cc)
    if bcc:
        msg['Bcc'] = ', '.join(bcc)
    if reply_to:
        msg['Reply-To'] = reply_to
    msg['Subject'] = subject
    msg['Message-ID'] = make_msgid(domain='certifai')

    if text and html:
        msg.set_content(text)
        msg.add_alternative(html, subtype='html')
    elif html:
        msg.set_content('Para ver este correo necesitas un cliente que soporte HTML.')
        msg.add_alternative(html, subtype='html')
    else:
        msg.set_content(text or '')

    if attachments:
        for filename, content, mime in attachments:
            maintype, _, subtype = mime.partition('/')
            msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)

    return msg


def send_email(*, to: str | list[str], subject: str,
               html: str | None = None, text: str | None = None,
               sender: str | None = None,
               cc: str | list[str] | None = None,
               bcc: str | list[str] | None = None,
               reply_to: str | None = None,
               attachments: list[tuple[str, bytes, str]] | None = None) -> str:
    """Envía un correo. Devuelve el message_id de Gmail.

    Args:
        attachments: lista de tuplas (filename, content_bytes, mime_type)
    """
    if isinstance(to, str):
        to = [to]
    if isinstance(cc, str):
        cc = [cc]
    if isinstance(bcc, str):
        bcc = [bcc]

    sender = sender or getattr(settings, 'DEFAULT_FROM_EMAIL', None) or settings.GOOGLE_OAUTH_EMAIL

    mime = _build_mime(
        sender=sender, to=to, subject=subject,
        html=html, text=text, cc=cc, bcc=bcc,
        reply_to=reply_to, attachments=attachments,
    )
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode('ascii')

    service = _build_service()
    try:
        result = service.users().messages().send(
            userId='me',
            body={'raw': raw},
        ).execute()
        msg_id = result.get('id', '')
        logger.info('Email enviado vía Gmail API: id=%s to=%s subject=%r', msg_id, to, subject)
        return msg_id
    except HttpError as e:
        logger.exception('Gmail API rechazó el envío: %s', e)
        raise


def send_django_email_message(email_message) -> str:
    """Adaptador para `django.core.mail.EmailMessage` y `EmailMultiAlternatives`."""
    from django.core.mail import EmailMultiAlternatives

    text_body = email_message.body or ''
    html_body = None
    if isinstance(email_message, EmailMultiAlternatives):
        for content, mime in email_message.alternatives or []:
            if mime == 'text/html':
                html_body = content
                break

    attachments = []
    for att in (email_message.attachments or []):
        # Tupla (filename, content, mimetype) o un MIMEBase
        if isinstance(att, tuple) and len(att) == 3:
            filename, content, mimetype = att
            if isinstance(content, str):
                content = content.encode('utf-8')
            attachments.append((filename, content, mimetype or 'application/octet-stream'))

    return send_email(
        to=list(email_message.to or []),
        subject=email_message.subject or '',
        html=html_body,
        text=text_body if text_body else None,
        sender=email_message.from_email or None,
        cc=list(email_message.cc or []) or None,
        bcc=list(email_message.bcc or []) or None,
        reply_to=(email_message.reply_to or [None])[0] if email_message.reply_to else None,
        attachments=attachments or None,
    )
