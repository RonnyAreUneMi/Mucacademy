"""Impersonación: un admin ve la app como un participante (estudiante/docente).

Aprovecha que la sesión de participante (`request.session['participant_id']`)
es independiente de la sesión admin (Django auth): el admin sigue autenticado,
así puede volver al panel en cualquier momento con "Salir".
"""
from django.shortcuts import get_object_or_404, redirect

from core.models import Participant
from ._shared import admin_required

IMPERSONATE_KEY = 'impersonating_by'
PARTICIPANT_SESSION_KEY = 'participant_id'


@admin_required
def impersonate_participant(request, id):
    """Inicia sesión de participante (manteniendo la sesión admin) y va a /cuenta/."""
    p = get_object_or_404(Participant, id=id)
    request.session[PARTICIPANT_SESSION_KEY] = p.id
    request.session[IMPERSONATE_KEY] = request.user.id
    return redirect('/cuenta/')


def stop_impersonation(request):
    """Termina la impersonación y vuelve al panel de participantes."""
    request.session.pop(PARTICIPANT_SESSION_KEY, None)
    request.session.pop(IMPERSONATE_KEY, None)
    return redirect('/panel/participantes/')
