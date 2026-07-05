"""Google Sign-In para participantes (distinto del admin Meet OAuth).

El admin usa Google para Meet/Calendar/Drive con la cuenta institucional.
Los participantes usan Google sólo para identificarse: scope mínimo
(openid email profile).

Flujo:
    /cuenta/google/start/    → redirige a Google con scopes de login
    /cuenta/google/callback/ → recibe code, verifica id_token, login
"""
from __future__ import annotations

import os

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from google_auth_oauthlib.flow import Flow

# Google a veces devuelve más scopes de los pedidos (con openid).
# Esta variable evita el "scope changed" error de oauthlib.
os.environ.setdefault('OAUTHLIB_RELAX_TOKEN_SCOPE', '1')

# Scopes mínimos para login: solo identidad
SIGNIN_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]


def _client_config(redirect_uri: str) -> dict:
    return {
        'web': {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': [redirect_uri],
        }
    }


def build_signin_flow(redirect_uri: str, state: str | None = None) -> Flow:
    flow = Flow.from_client_config(
        _client_config(redirect_uri),
        scopes=SIGNIN_SCOPES,
        state=state,
    )
    flow.redirect_uri = redirect_uri
    return flow


def fetch_userinfo_from_idtoken(id_token_str: str) -> dict:
    """Verifica el JWT id_token devuelto por Google y extrae los datos del user.

    Devuelve dict con: email, given_name, family_name, picture, sub (Google user id).
    Lanza ValueError si el token no es válido.

    `clock_skew_in_seconds=30` tolera drift entre el reloj local y los servidores
    de Google (evita "Token used too early" cuando la PC está unos segundos
    desfasada).
    """
    idinfo = google_id_token.verify_oauth2_token(
        id_token_str,
        google_requests.Request(),
        settings.GOOGLE_CLIENT_ID,
        clock_skew_in_seconds=30,
    )
    return {
        'email': idinfo.get('email', ''),
        'email_verified': idinfo.get('email_verified', False),
        'given_name': idinfo.get('given_name', ''),
        'family_name': idinfo.get('family_name', ''),
        'picture': idinfo.get('picture', ''),
        'sub': idinfo.get('sub', ''),
    }
