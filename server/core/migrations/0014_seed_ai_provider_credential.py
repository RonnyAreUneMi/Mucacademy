"""Siembra una AIProviderCredential desde el AIConfig singleton existente.

Así la config previa (proveedor + modelo + api_key) sigue funcionando con el
nuevo sistema multi-proveedor + fallback. Usa los modelos reales porque el
api_key es un campo cifrado (Fernet) que necesita sus métodos.
"""
from django.db import migrations


def seed(apps, schema_editor):
    # Modelos reales: el campo cifrado necesita su lógica de encrypt/decrypt.
    from core.models import AIConfig, AIProviderCredential
    cfg = AIConfig.objects.filter(pk=1).first()
    if cfg is None:
        return
    if not (cfg.provider and cfg.api_key and cfg.model):
        return
    if AIProviderCredential.objects.filter(provider=cfg.provider).exists():
        return
    AIProviderCredential.objects.create(
        provider=cfg.provider,
        api_key=cfg.api_key,
        model=cfg.model,
        enabled=cfg.enabled,
        priority=10,
    )


def unseed(apps, schema_editor):
    pass  # no revertimos: es una copia idempotente


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0013_aiprompt_aiprovidercredential'),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]
