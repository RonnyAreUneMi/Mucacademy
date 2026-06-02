"""DRF Authentication para participantes vía bearer token.

Uso desde el cliente móvil:
    Authorization: Token <key>

El backend valida que el token exista, no esté expirado y devuelve el
Participant correspondiente envuelto en `request.user` (proxy mínimo
para compatibilidad con permission_classes de DRF).
"""
from __future__ import annotations

from django.utils import timezone
from rest_framework import authentication, exceptions

from core.models import ParticipantToken


class _ParticipantPrincipal:
    """Wrapper que hace que `request.user` sea compatible con DRF.

    Define `is_authenticated=True` y expone el participante real como
    `request.user.participant`.
    """
    def __init__(self, participant):
        self.participant = participant
        self.is_authenticated = True
        self.is_anonymous = False
        self.is_staff = False
        self.is_superuser = False
        self.id = participant.id
        self.pk = participant.pk
        self.email = participant.email
        self.username = participant.email

    def __str__(self):
        return f'Participant<{self.email}>'


class ParticipanteTokenAuthentication(authentication.BaseAuthentication):
    keyword = 'Token'

    def authenticate(self, request):
        header = request.META.get('HTTP_AUTHORIZATION', '')
        if not header.startswith(self.keyword + ' '):
            return None

        key = header.split(' ', 1)[1].strip()
        if not key:
            raise exceptions.AuthenticationFailed('Token vacío.')

        try:
            tok = ParticipantToken.objects.select_related('participant').get(key=key)
        except ParticipantToken.DoesNotExist:
            raise exceptions.AuthenticationFailed('Token inválido.')

        if tok.is_expired:
            raise exceptions.AuthenticationFailed('Token expirado.')

        # Touch last_used (sin disparar updated_at)
        ParticipantToken.objects.filter(pk=tok.pk).update(last_used_at=timezone.now())

        return (_ParticipantPrincipal(tok.participant), tok)

    def authenticate_header(self, request):
        return self.keyword
