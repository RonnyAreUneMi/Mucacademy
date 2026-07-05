"""Field types personalizados, foco en seguridad de datos sensibles.

`EncryptedTextField` cifra el valor at-rest en la BD usando Fernet (AES-128
en modo CBC + HMAC). La clave se deriva de `settings.SECRET_KEY`, por lo que
NO se necesita una key adicional, pero al rotar `SECRET_KEY` los datos
cifrados con la key anterior quedan inaccesibles (rotación = pérdida).

Uso:
    from core.base.fields import EncryptedTextField, EncryptedCharField

    class AIConfig(models.Model):
        api_key = EncryptedCharField(max_length=500, blank=True, default='')

Las lecturas son transparentes: `obj.api_key` devuelve el texto plano. Las
escrituras también: `obj.api_key = 'sk-…'` se cifra al guardar.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _get_fernet() -> Fernet:
    """Deriva una key Fernet (32 bytes b64) de `settings.SECRET_KEY`.

    SHA-256 del secret → 32 bytes → base64 url-safe (formato Fernet).
    """
    digest = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    key_b64 = base64.urlsafe_b64encode(digest)
    return Fernet(key_b64)


def _encrypt(value: str) -> str:
    if not value:
        return ''
    f = _get_fernet()
    return f.encrypt(value.encode('utf-8')).decode('ascii')


def _decrypt(value: str) -> str:
    if not value:
        return ''
    f = _get_fernet()
    try:
        return f.decrypt(value.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError):
        # Valor no cifrado (legacy en plain text) o key cambiada — devolvemos
        # tal cual para no romper datos existentes. Al guardar se cifrará.
        return value


class EncryptedTextField(models.TextField):
    """`TextField` cifrado at-rest. API idéntica a TextField."""

    description = 'Texto cifrado con Fernet (AES-128 + HMAC)'

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return _decrypt(value)

    def to_python(self, value):
        if value is None or value == '':
            return value
        # Si viene de la BD ya pasó por from_db_value; si es asignación nueva
        # devolvemos como está (texto plano).
        return value

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        return _encrypt(str(value))


class EncryptedCharField(models.CharField):
    """`CharField` cifrado at-rest. Ojo: el `max_length` debe contemplar el
    overhead de Fernet (~100 chars extra para tokens cortos). Para valores
    largos preferir `EncryptedTextField`.
    """

    description = 'Char cifrado con Fernet (AES-128 + HMAC)'

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return _decrypt(value)

    def to_python(self, value):
        if value is None or value == '':
            return value
        return value

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        return _encrypt(str(value))
