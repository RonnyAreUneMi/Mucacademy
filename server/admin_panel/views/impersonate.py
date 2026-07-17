"""Impersonación: un admin ve la app como un participante (estudiante/docente).

Aprovecha que la sesión de participante (`request.session['participant_id']`)
es independiente de la sesión admin (Django auth): el admin sigue autenticado,
así puede volver al panel en cualquier momento con "Salir".
"""
from django.contrib.auth import login
from django.shortcuts import get_object_or_404, redirect

from core.models import Participant, User
from ._shared import admin_required, superadmin_required

IMPERSONATE_KEY = 'impersonating_by'
PARTICIPANT_SESSION_KEY = 'participant_id'
USER_IMPERSONATOR_KEY = 'impersonator_id'
_AUTH_BACKEND = 'admin_panel.backends.EmailBackend'


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


@superadmin_required
def impersonate_user(request, id):
    """El superadmin inicia sesión como otro usuario del panel para ver su vista."""
    target = get_object_or_404(User, id=id)
    if target.id == request.user.id:
        return redirect('panel:usuarios_list')
    original_id = request.user.id
    login(request, target, backend=_AUTH_BACKEND)
    request.session[USER_IMPERSONATOR_KEY] = original_id
    if target.role in ('admin', 'superadmin'):
        return redirect('panel:dashboard')
    return redirect('panel:mi_estado')


def stop_user_impersonation(request):
    """Vuelve a la cuenta del superadmin que inició la impersonación."""
    original_id = request.session.pop(USER_IMPERSONATOR_KEY, None)
    if original_id:
        original = User.objects.filter(id=original_id).first()
        if original:
            login(request, original, backend=_AUTH_BACKEND)
    return redirect('panel:usuarios_list')
