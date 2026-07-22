"""Views para conectar la cuenta Google institucional.

Flujo:
    /admin/google/connect/   → redirige a Google consent
    /admin/google/callback/  → recibe `code`, guarda tokens, vuelve a panel
    /admin/google/status/    → JSON con estado de la conexión
"""
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from core.models import GoogleCredential
from core.services.meet import oauth as goauth

from ._shared import _is_superadmin, _log_audit
from core.security.decorators import module_required


@login_required
@user_passes_test(_is_superadmin)
@module_required('google')
def google_config(request):
    """Pantalla de administración de la integración Google Cloud (Meet/Calendar/Drive)."""
    cred = GoogleCredential.get_singleton()
    has_oauth = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    return render(request, 'panel/google/config.html', {
        'cred': cred,
        'connected': cred is not None,
        'has_oauth_config': has_oauth,
        'oauth_email_hint': settings.GOOGLE_OAUTH_EMAIL,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'scopes': getattr(settings, 'GOOGLE_OAUTH_SCOPES', []),
    })


@login_required
@user_passes_test(_is_superadmin)
@require_http_methods(['POST'])
def google_disconnect(request):
    """Desvincula la cuenta Google (borra la credencial guardada)."""
    n, _ = GoogleCredential.objects.all().delete()
    if n:
        _log_audit(request.user, 'DELETE', 'Cuenta Google desvinculada')
        messages.success(request, 'Cuenta de Google desvinculada. Las sesiones virtuales ya no generarán Meet automático hasta reconectar.')
    else:
        messages.info(request, 'No había ninguna cuenta de Google conectada.')
    return redirect('panel:google_config')


@login_required
@user_passes_test(_is_superadmin)
def google_connect(request):
    """Inicia el flujo OAuth — redirige a la pantalla de consent de Google."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        messages.error(
            request,
            'Falta configurar GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET en .env.',
        )
        return redirect('panel:dashboard')

    flow = goauth.build_flow()
    auth_url, state = flow.authorization_url(
        access_type='offline',           # imprescindible para obtener refresh_token
        include_granted_scopes='true',
        prompt='consent',                # fuerza re-consent → garantiza refresh_token
    )
    request.session['google_oauth_state'] = state
    # PKCE: guardar el code_verifier para mandarlo en el callback (sino fetch_token falla)
    request.session['google_oauth_code_verifier'] = flow.code_verifier
    return HttpResponseRedirect(auth_url)


@login_required
@user_passes_test(_is_superadmin)
def google_callback(request):
    """Recibe el `code` de Google, intercambia por tokens y los persiste."""
    error = request.GET.get('error')
    if error:
        messages.error(request, f'Google rechazó la autorización: {error}')
        return redirect('panel:dashboard')

    state = request.session.pop('google_oauth_state', None)
    code_verifier = request.session.pop('google_oauth_code_verifier', None)
    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Google no devolvió un code de autorización.')
        return redirect('panel:dashboard')

    try:
        flow = goauth.build_flow(state=state)
        if code_verifier:
            flow.code_verifier = code_verifier  # restaurar PKCE verifier
        flow.fetch_token(code=code)
        creds = flow.credentials
        email = goauth.fetch_user_email(creds) or settings.GOOGLE_OAUTH_EMAIL
        goauth.save_credentials(creds, email=email)
    except Exception as exc:  # pragma: no cover — fallback de seguridad
        messages.error(request, f'Error procesando OAuth: {exc}')
        return redirect('panel:dashboard')

    messages.success(
        request,
        f'Cuenta Google conectada correctamente: {email}. '
        f'Ya podés crear sesiones virtuales con link Meet automático.',
    )
    return redirect('panel:dashboard')


@login_required
@user_passes_test(_is_superadmin)
def google_status(request):
    """JSON con el estado de la conexión Google (para el dashboard)."""
    cred = GoogleCredential.get_singleton()
    if cred is None:
        return JsonResponse({
            'connected': False,
            'connect_url': reverse('panel:google_connect'),
        })
    return JsonResponse({
        'connected': True,
        'email': cred.email,
        'scopes': cred.scopes,
        'expires_at': cred.expiry.isoformat() if cred.expiry else None,
        'connected_since': cred.created_at.isoformat(),
        'reconnect_url': reverse('panel:google_connect'),
    })
