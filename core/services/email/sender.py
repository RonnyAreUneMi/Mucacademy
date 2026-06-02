"""Helpers para correos transaccionales con plantillas HTML.

Cada función renderiza el template con su contexto, agrega contexto común
(URLs, email destino) y delega en `gmail.send_email()`.

Diseño defensivo: si el envío falla por config faltante (sin OAuth, sin
scope) sólo lo logueamos y devolvemos False — no rompemos el flow del
user. Si más adelante quieres que falle ruidosamente, quita el try/except.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.template.loader import render_to_string

from core.models import Participant
from core.services.email.gmail import send_email, GmailNotConfigured

logger = logging.getLogger(__name__)


def _site_url(request=None) -> str:
    """URL base del sitio. Usa el host del request si está disponible, o setting."""
    if request is not None:
        try:
            return f'{request.scheme}://{request.get_host()}'
        except Exception:
            pass
    return getattr(settings, 'SITE_URL', 'http://localhost:8500')


def _user_agent_short(request) -> str:
    """Resumen legible del User-Agent para el correo."""
    if request is None:
        return ''
    ua = request.META.get('HTTP_USER_AGENT', '') or ''
    if not ua:
        return ''
    # Heurísticas simples — para producción real, usar `user-agents` package
    browser = 'Navegador'
    if 'Edg/' in ua: browser = 'Edge'
    elif 'Chrome/' in ua and 'Safari/' in ua: browser = 'Chrome'
    elif 'Firefox/' in ua: browser = 'Firefox'
    elif 'Safari/' in ua: browser = 'Safari'
    os_name = 'Dispositivo'
    if 'Windows' in ua: os_name = 'Windows'
    elif 'Mac OS' in ua or 'Macintosh' in ua: os_name = 'macOS'
    elif 'Android' in ua: os_name = 'Android'
    elif 'iPhone' in ua or 'iPad' in ua: os_name = 'iOS'
    elif 'Linux' in ua: os_name = 'Linux'
    return f'{browser} en {os_name}'


def _client_ip(request) -> str:
    if request is None:
        return ''
    fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _safe_send(*, template: str, subject: str, to: str, context: dict) -> bool:
    """Renderiza el template y manda el correo. No rompe si falla."""
    try:
        html = render_to_string(template, context)
        send_email(to=to, subject=subject, html=html)
        return True
    except GmailNotConfigured as e:
        logger.warning('Gmail no configurado, correo "%s" descartado: %s', subject, e)
        return False
    except Exception:
        logger.exception('Fallo al enviar correo transaccional "%s" a %s', subject, to)
        return False


# ════════════════════════════════════════════════════════════════
# Bienvenida (al registrarse)
# ════════════════════════════════════════════════════════════════

def send_welcome_email(participante: Participant, request=None) -> bool:
    site = _site_url(request)
    return _safe_send(
        template='emails/welcome.html',
        subject=f'¡Bienvenido a CertifAI, {participante.first_name}!',
        to=participante.email,
        context={
            'p': participante,
            'to_email': participante.email,
            'site_url': site,
            'dashboard_url': f'{site}/cuenta/',
        },
    )


# ════════════════════════════════════════════════════════════════
# Notificación de inicio de sesión
# ════════════════════════════════════════════════════════════════

def send_login_notification(participante: Participant, *, method: str, request=None) -> bool:
    """Envía aviso de nuevo login.

    Args:
        method: 'Email y contraseña' | 'Google' | etc.
    """
    from django.utils import timezone
    site = _site_url(request)
    return _safe_send(
        template='emails/login_notification.html',
        subject='Nuevo inicio de sesión en tu cuenta',
        to=participante.email,
        context={
            'p': participante,
            'to_email': participante.email,
            'site_url': site,
            'profile_url': f'{site}/cuenta/perfil/',
            'login_at': timezone.localtime(),
            'login_method': method,
            'device': _user_agent_short(request),
            'ip_address': _client_ip(request),
        },
    )


# ════════════════════════════════════════════════════════════════
# Inscripción a un evento
# ════════════════════════════════════════════════════════════════

def _gcal_add_url(sesion) -> str:
    """Construye un link 'Add to Google Calendar' con los datos del evento."""
    from datetime import datetime
    from urllib.parse import urlencode
    start = datetime.combine(sesion.date, sesion.start_time)
    end   = datetime.combine(sesion.date, sesion.end_time)
    fmt = '%Y%m%dT%H%M%S'  # local time, sin Z (Google interpreta como tz del user)
    title = sesion.title or sesion.day_of_week
    location = ''
    if getattr(sesion, 'is_virtual', False):
        location = getattr(sesion, 'meeting_url', '') or 'Google Meet'
    else:
        location = getattr(sesion, 'location', '') or ''
    details = f'Te inscribiste a este evento desde CertifAI.'
    if getattr(sesion, 'meeting_url', None):
        details += f'\n\nLink: {sesion.meeting_url}'
    params = {
        'action': 'TEMPLATE',
        'text':   title,
        'dates':  f'{start.strftime(fmt)}/{end.strftime(fmt)}',
        'details': details,
        'location': location,
    }
    return f'https://www.google.com/calendar/render?{urlencode(params)}'


def send_certificate_issued(*, certificado, sesion, participante: Participant, request=None) -> bool:
    """Notifica al participante que su certificado fue emitido.

    Si `participante` es None (caso bulk con sólo email/cedula), se intenta
    resolver desde el certificado.
    """
    site = _site_url(request)
    to_email = (participante.email if participante else certificado.email or '').strip()
    if not to_email:
        return False

    # Para mostrar en el correo: contexto compatible con Participant real o certificado-only
    p_ctx = participante or type('P', (), {
        'first_name': certificado.first_name or 'participante',
        'last_name': certificado.last_name or '',
        'email': certificado.email or '',
        'full_name': f'{certificado.first_name} {certificado.last_name}'.strip(),
    })()

    hash_full = str(getattr(certificado, 'verification_hash', '') or '')
    hash_short = hash_full[:8].upper() if hash_full else ''

    return _safe_send(
        template='emails/certificate_issued.html',
        subject=f'Tu certificado de "{sesion.title or sesion.day_of_week}" ya está listo',
        to=to_email,
        context={
            'p': p_ctx,
            'to_email': to_email,
            'site_url': site,
            'sesion': sesion,
            'cert_horas': getattr(certificado, 'hours', None),
            'cert_hash_short': hash_short,
            'certs_url': f'{site}/cuenta/certificados/',
            'download_url': f'{site}/api/v1/public/certificates/{hash_full}/download/' if hash_full else None,
        },
    )


def send_event_inscription(participante: Participant, sesion, request=None) -> bool:
    """Envía confirmación cuando un user se inscribe a un evento."""
    from django.utils import timezone
    site = _site_url(request)
    today = timezone.localdate()
    days_until = (sesion.date - today).days
    fecha_iso = sesion.date.isoformat()  # YYYY-MM-DD para el deep link
    return _safe_send(
        template='emails/event_inscription.html',
        subject=f'Te inscribiste a {sesion.title or sesion.day_of_week}',
        to=participante.email,
        context={
            'p': participante,
            'to_email': participante.email,
            'site_url': site,
            'sesion': sesion,
            'days_until': days_until,
            'calendar_url': f'{site}/cuenta/?day={fecha_iso}',
            'events_url':   f'{site}/cuenta/eventos/?tab=mios',
            'gcal_url': _gcal_add_url(sesion),
        },
    )
