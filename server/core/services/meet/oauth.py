"""Flujo OAuth 2.0 con Google: build → save → get/refresh.

Uso típico:
    flow = build_flow()
    auth_url, state = flow.authorization_url(...)
    # ... usuario autoriza, vuelve con `code` ...
    flow.fetch_token(code=code)
    save_credentials(flow.credentials)

    # Después, en cualquier momento:
    creds = get_credentials()  # auto-refresca si expiró
    service = build('calendar', 'v3', credentials=creds)
"""
from __future__ import annotations

from datetime import datetime, timezone

from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from core.models import GoogleCredential


def _client_config() -> dict:
    """Construye el dict que espera Flow.from_client_config()."""
    return {
        'web': {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': [settings.GOOGLE_REDIRECT_URI],
        }
    }


def build_flow(state: str | None = None) -> Flow:
    """Crea el Flow OAuth con los scopes configurados."""
    flow = Flow.from_client_config(
        _client_config(),
        scopes=settings.GOOGLE_OAUTH_SCOPES,
        state=state,
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow


def save_credentials(creds: Credentials, email: str) -> GoogleCredential:
    """Persiste o actualiza el access + refresh token en DB."""
    obj, _created = GoogleCredential.objects.update_or_create(
        email=email,
        defaults={
            'access_token': creds.token or '',
            'refresh_token': creds.refresh_token or '',
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': list(creds.scopes or []),
            'expiry': creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None,
        },
    )
    return obj


def get_credentials() -> Credentials | None:
    """Recupera credenciales guardadas. Auto-refresca si expiraron.

    Devuelve None si no hay nadie conectado todavía.
    """
    cred = GoogleCredential.get_singleton()
    if cred is None:
        return None

    creds = Credentials(
        token=cred.access_token,
        refresh_token=cred.refresh_token or None,
        token_uri=cred.token_uri,
        client_id=cred.client_id,
        client_secret=cred.client_secret,
        scopes=cred.scopes,
    )
    if cred.expiry:
        creds.expiry = cred.expiry.replace(tzinfo=None)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Persistimos el nuevo access_token
        cred.access_token = creds.token or ''
        cred.expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None
        cred.save(update_fields=['access_token', 'expiry', 'updated_at'])

    return creds


def fetch_user_email(creds: Credentials) -> str:
    """Llama userinfo para saber qué cuenta acaba de autorizar."""
    from googleapiclient.discovery import build
    service = build('oauth2', 'v2', credentials=creds)
    info = service.userinfo().get().execute()
    return info.get('email', '')
