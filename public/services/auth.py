"""Auth de cuentas públicas (Participant).

No usamos Django's auth.User para `Participant` porque ya existe el flujo
guest (registrarse a un evento sin cuenta) y queremos preservarlo.

En vez de eso, mantenemos una sesión simple via `request.session['participant_id']`.
Compatible con el middleware de sesión de Django.
"""
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone

from core.models import Participant

SESSION_KEY = 'participant_id'


def authenticate(email: str, password: str) -> Participant | None:
    """Devuelve el Participant si credenciales son válidas; None si no."""
    if not email or not password:
        return None
    try:
        p = Participant.objects.get(email__iexact=email.strip())
    except Participant.DoesNotExist:
        return None
    if not p.has_account:
        return None
    if not p.check_password(password):
        return None
    return p


def login(request, participant: Participant) -> None:
    """Setea la sesión y actualiza last_login."""
    request.session[SESSION_KEY] = participant.id
    participant.last_login = timezone.now()
    participant.save(update_fields=['last_login'])


def logout(request) -> None:
    request.session.pop(SESSION_KEY, None)


def get_current_participant(request) -> Participant | None:
    """Recupera el Participant de la sesión, o None si no logueado."""
    pid = request.session.get(SESSION_KEY)
    if not pid:
        return None
    try:
        return Participant.objects.get(pk=pid)
    except Participant.DoesNotExist:
        request.session.pop(SESSION_KEY, None)
        return None


def login_required(view_func):
    """Decorator: redirige a login si no hay sesión activa de participante."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        p = get_current_participant(request)
        if not p:
            messages.info(request, 'Iniciá sesión para acceder a tu cuenta.')
            return redirect(f'/cuenta/login/?next={request.path}')
        request.participant = p
        return view_func(request, *args, **kwargs)
    return wrapper
