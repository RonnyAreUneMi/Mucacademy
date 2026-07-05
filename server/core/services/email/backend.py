"""Django EmailBackend que envía vía Gmail API en vez de SMTP.

Permite usar `send_mail()`, `EmailMessage.send()`, etc. de forma estándar.

Activación en settings.py:
    EMAIL_BACKEND = 'core.services.email.backend.GmailAPIBackend'
"""
from __future__ import annotations

import logging

from django.core.mail.backends.base import BaseEmailBackend

from core.services.email.gmail import send_django_email_message, GmailNotConfigured

logger = logging.getLogger(__name__)


class GmailAPIBackend(BaseEmailBackend):
    """Envía cada `EmailMessage` por la Gmail API de la cuenta institucional."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        sent = 0
        for message in email_messages:
            try:
                send_django_email_message(message)
                sent += 1
            except GmailNotConfigured as exc:
                if not self.fail_silently:
                    raise
                logger.warning('Gmail no configurado, correo descartado: %s', exc)
            except Exception:
                if not self.fail_silently:
                    raise
                logger.exception('Fallo al enviar correo via Gmail API')
        return sent
