"""Cliente IA multi-proveedor (Claude / OpenAI / Groq).

Lee la configuración desde el modelo `AIConfig` (singleton). Si no hay
configuración guardada o está deshabilitada, intenta el fallback por
variable de entorno `ANTHROPIC_API_KEY` (compat con scripts/CLI).

Los SDKs se importan de forma lazy para no fallar si no están instalados.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class AIRuntime:
    """Configuración resuelta lista para hacer una llamada."""
    provider: str
    model: str
    api_key: str
    temperature: float
    max_tokens: int
    system_prefix: str = ''


@dataclass
class AIResponse:
    """Respuesta enriquecida con tracking de tokens (uso/costo)."""
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ''


def _global_params():
    """Parámetros globales de generación (AIConfig singleton) + master switch."""
    try:
        from core.models import AIConfig
        cfg = AIConfig.objects.filter(pk=1).first()
    except Exception:
        cfg = None
    if cfg is None:
        return True, 0.7, 1024, ''   # sin config → permitir (usa env)
    return bool(cfg.enabled), cfg.temperature, cfg.max_tokens, cfg.system_prompt_override or ''


def _runtime_from_env() -> AIRuntime | None:
    """Fallback: si hay ANTHROPIC_API_KEY usamos Claude."""
    key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not key:
        return None
    return AIRuntime(
        provider='claude',
        model='claude-haiku-4-5-20251001',
        api_key=key,
        temperature=0.7,
        max_tokens=1024,
    )


def get_runtime_chain() -> list[AIRuntime]:
    """Cadena ordenada de runtimes para fallback automático.

    Master switch (AIConfig.enabled) gobierna todo. Devuelve los proveedores
    habilitados con api_key + modelo, ordenados por prioridad. Si no hay
    ninguno configurado, cae al env (ANTHROPIC_API_KEY) para CLI/tests.
    """
    enabled_master, temperature, max_tokens, prefix = _global_params()
    if not enabled_master:
        return []

    chain: list[AIRuntime] = []
    try:
        from core.models import AIProviderCredential
        creds = list(AIProviderCredential.objects.filter(enabled=True).order_by('priority', 'provider'))
        for c in creds:
            if c.api_key and c.model:
                chain.append(AIRuntime(
                    provider=c.provider, model=c.model, api_key=c.api_key,
                    temperature=temperature, max_tokens=max_tokens, system_prefix=prefix,
                ))
    except Exception:
        pass

    # Backward-compat: si no hay credenciales nuevas, intentamos el AIConfig legacy.
    if not chain:
        try:
            from core.models import AIConfig
            cfg = AIConfig.objects.filter(pk=1).first()
            if cfg is not None and cfg.api_key and cfg.model:
                chain.append(AIRuntime(
                    provider=cfg.provider, model=cfg.model, api_key=cfg.api_key,
                    temperature=temperature, max_tokens=max_tokens, system_prefix=prefix,
                ))
        except Exception:
            pass

    if not chain:
        env_rt = _runtime_from_env()
        if env_rt is not None:
            chain.append(env_rt)
    return chain


def get_runtime() -> AIRuntime | None:
    """Runtime primario (primero de la cadena). Compat con código existente."""
    chain = get_runtime_chain()
    return chain[0] if chain else None


def get_runtime_for(provider: str) -> AIRuntime | None:
    """Runtime de un proveedor específico en la cadena (o None).

    Útil para features atadas a un proveedor (ej. generación de imágenes = OpenAI).
    """
    for rt in get_runtime_chain():
        if rt.provider == provider:
            return rt
    return None


def is_configured() -> bool:
    return bool(get_runtime_chain())


# ── Dispatchers por proveedor ─────────────────────────────────

def _call_claude(rt: AIRuntime, system: str, user: str) -> str:
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError('SDK `anthropic` no instalado. Ejecutá: pip install anthropic') from exc
    client = Anthropic(api_key=rt.api_key)
    resp = client.messages.create(
        model=rt.model,
        max_tokens=rt.max_tokens,
        temperature=rt.temperature,
        system=[{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}],
        messages=[{'role': 'user', 'content': user}],
    )
    return resp.content[0].text


def _call_openai_compatible(rt: AIRuntime, system: str, user: str, base_url: str | None = None) -> str:
    """Funciona para OpenAI y Groq (Groq expone API compatible con OpenAI)."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError('SDK `openai` no instalado. Ejecutá: pip install openai') from exc
    client = OpenAI(api_key=rt.api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=rt.model,
        max_tokens=rt.max_tokens,
        temperature=rt.temperature,
        messages=[
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
    )
    return resp.choices[0].message.content or ''


def call_ai_with_runtime(rt: AIRuntime, system: str, user: str) -> str:
    """Llama al proveedor del runtime dado. No lee DB — útil para tests."""
    return call_ai_full(rt, system, user).text


def call_ai_full(rt: AIRuntime, system: str, user: str) -> AIResponse:
    """Como `call_ai_with_runtime` pero devuelve tokens también.

    Útil cuando se quiere registrar el uso/costo (ej. resumen de transcript).
    """
    full_system = (rt.system_prefix + '\n\n' + system).strip() if rt.system_prefix else system
    if rt.provider == 'claude':
        return _call_claude_full(rt, full_system, user)
    if rt.provider == 'openai':
        return _call_openai_full(rt, full_system, user)
    if rt.provider == 'groq':
        return _call_openai_full(rt, full_system, user, base_url='https://api.groq.com/openai/v1')
    raise NotImplementedError(f'Proveedor no soportado: {rt.provider}')


def _call_claude_full(rt: AIRuntime, system: str, user: str) -> AIResponse:
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError('SDK `anthropic` no instalado. Ejecutá: pip install anthropic') from exc
    client = Anthropic(api_key=rt.api_key)
    resp = client.messages.create(
        model=rt.model,
        max_tokens=rt.max_tokens,
        temperature=rt.temperature,
        system=[{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}],
        messages=[{'role': 'user', 'content': user}],
    )
    usage = getattr(resp, 'usage', None)
    return AIResponse(
        text=resp.content[0].text,
        input_tokens=getattr(usage, 'input_tokens', 0) if usage else 0,
        output_tokens=getattr(usage, 'output_tokens', 0) if usage else 0,
        model=rt.model,
    )


def _call_openai_full(rt: AIRuntime, system: str, user: str, base_url: str | None = None) -> AIResponse:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError('SDK `openai` no instalado. Ejecutá: pip install openai') from exc
    client = OpenAI(api_key=rt.api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=rt.model,
        max_tokens=rt.max_tokens,
        temperature=rt.temperature,
        messages=[
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
    )
    usage = getattr(resp, 'usage', None)
    return AIResponse(
        text=resp.choices[0].message.content or '',
        input_tokens=getattr(usage, 'prompt_tokens', 0) if usage else 0,
        output_tokens=getattr(usage, 'completion_tokens', 0) if usage else 0,
        model=rt.model,
    )


def generate(system: str, user: str) -> AIResponse:
    """Punto único con FALLBACK automático entre proveedores.

    Recorre la cadena (ordenada por prioridad); si un proveedor falla
    (sin crédito, error, timeout, SDK ausente), reintenta con el siguiente.

    Lanza NotImplementedError si no hay ningún proveedor configurado.
    Relanza el último error si todos fallan.
    """
    chain = get_runtime_chain()
    if not chain:
        raise NotImplementedError(
            'IA no configurada. Andá a /panel/ai/config/ y activá un proveedor + API key.'
        )
    last_exc: Exception | None = None
    for i, rt in enumerate(chain):
        try:
            return call_ai_full(rt, system, user)
        except Exception as exc:  # noqa: BLE001 — probamos el siguiente proveedor
            log.warning('Proveedor %s falló (%s). %s',
                        rt.provider, exc,
                        'Probando siguiente…' if i + 1 < len(chain) else 'Sin más fallbacks.')
            last_exc = exc
            continue
    raise last_exc if last_exc else RuntimeError('Todos los proveedores de IA fallaron.')


def call_ai(system: str, user: str) -> str:
    """Punto único de entrada (texto) — usa la cadena con fallback automático."""
    return generate(system, user).text


# ── Compat con código existente ───────────────────────────────

def call_claude(system: str, user: str, model: str | None = None, max_tokens: int | None = None) -> str:
    """Wrapper compat. Ignora `model`/`max_tokens` (los toma de AIConfig)."""
    return call_ai(system, user)


def get_claude_client():
    """Compat — devuelve un cliente Anthropic si está configurado, si no None."""
    rt = get_runtime()
    if rt is None or rt.provider != 'claude':
        return None
    try:
        from anthropic import Anthropic
        return Anthropic(api_key=rt.api_key)
    except ImportError:
        return None
