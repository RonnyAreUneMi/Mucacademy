"""External service credentials (Google Workspace) and AI configuration.

`GoogleCredential` holds the OAuth tokens for the institutional account that
organizes Meets. `AIConfig` is a singleton with the active AI provider config.
Sensitive fields are encrypted at rest with Fernet (AES-128 + HMAC).
"""
from django.db import models

from core.base.fields import EncryptedCharField, EncryptedTextField
from core.base.models import SingletonModel, TimestampedModel


class GoogleCredential(TimestampedModel):
    """OAuth 2.0 access + refresh tokens for a Google account.

    Convention: a single row holds the institutional account. Tokens and
    client_secret are encrypted at rest (transparent read/write).
    """
    email = models.EmailField(unique=True, help_text='Connected Google account')
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField(help_text='Long-lived token for auto-refresh')
    token_uri = models.URLField(default='https://oauth2.googleapis.com/token')
    client_id = models.CharField(max_length=200)
    client_secret = EncryptedCharField(max_length=500, help_text='Encrypted at rest with Fernet')
    scopes = models.JSONField(default=list)
    expiry = models.DateTimeField(null=True, blank=True, help_text='When the access_token expires')

    class Meta:
        verbose_name = 'Google Credential'
        verbose_name_plural = 'Google Credentials'

    def __str__(self) -> str:
        return f'GoogleCredential<{self.email}>'

    @classmethod
    def get_singleton(cls) -> 'GoogleCredential | None':
        """Return the first registered credential (or None)."""
        return cls.objects.first()


class AIProvider(models.TextChoices):
    CLAUDE = 'claude', 'Anthropic Claude'
    OPENAI = 'openai', 'OpenAI (GPT)'
    GROQ = 'groq', 'Groq (Llama / Mixtral)'


# Suggested models per provider (for the form dropdown).
PROVIDER_MODELS = {
    AIProvider.CLAUDE: [
        ('claude-haiku-4-5-20251001', 'Claude Haiku 4.5 (fast & cheap)'),
        ('claude-sonnet-4-6', 'Claude Sonnet 4.6 (balanced)'),
        ('claude-opus-4-7', 'Claude Opus 4.7 (highest quality)'),
    ],
    AIProvider.OPENAI: [
        ('gpt-4o-mini', 'GPT-4o mini (fast & cheap)'),
        ('gpt-4o', 'GPT-4o (balanced)'),
        ('gpt-4-turbo', 'GPT-4 Turbo'),
    ],
    AIProvider.GROQ: [
        ('llama-3.3-70b-versatile', 'Llama 3.3 70B (recommended)'),
        ('llama-3.1-8b-instant', 'Llama 3.1 8B (ultra fast)'),
        ('mixtral-8x7b-32768', 'Mixtral 8×7B'),
    ],
}


class AIProviderCredential(TimestampedModel):
    """Credencial + modelo por proveedor, con orden de fallback.

    Se pueden guardar varias (una por proveedor). En runtime se arma una
    cadena ordenada por `priority` (menor = se intenta primero) entre las
    habilitadas con api_key y modelo; si una falla, se reintenta con la
    siguiente automáticamente.
    """
    provider = models.CharField(
        max_length=20, choices=AIProvider.choices, unique=True,
        verbose_name='Proveedor',
    )
    api_key = EncryptedCharField(
        max_length=1000, blank=True, default='',
        help_text='Cifrada en reposo con Fernet.',
    )
    model = models.CharField(
        max_length=80, blank=True, default='',
        verbose_name='Modelo',
        help_text='Identificador del modelo (ej. gpt-4o-mini).',
    )
    enabled = models.BooleanField(default=False, verbose_name='Habilitado')
    priority = models.PositiveSmallIntegerField(
        default=100, verbose_name='Prioridad (menor = primero)',
    )

    class Meta:
        verbose_name = 'AI Provider Credential'
        verbose_name_plural = 'AI Provider Credentials'
        ordering = ['priority', 'provider']

    def __str__(self) -> str:
        return f'{self.provider}:{self.model} (p{self.priority}, {"on" if self.enabled else "off"})'

    def is_ready(self) -> bool:
        return self.enabled and bool(self.api_key) and bool(self.model)

    def masked_api_key(self) -> str:
        if not self.api_key:
            return ''
        if len(self.api_key) <= 8:
            return '••••••••'
        return f'{self.api_key[:4]}••••••••{self.api_key[-4:]}'


class AIPrompt(TimestampedModel):
    """Prompt de sistema editable por cada feature de IA.

    `content` vacío = usar el prompt por defecto del código (registry en
    `core.services.ai.prompts`). Así 'restaurar por defecto' = vaciar content.
    """
    key = models.CharField(max_length=50, unique=True, verbose_name='Feature')
    content = models.TextField(blank=True, default='', verbose_name='Prompt')

    class Meta:
        verbose_name = 'AI Prompt'
        verbose_name_plural = 'AI Prompts'
        ordering = ['key']

    def __str__(self) -> str:
        return f'AIPrompt<{self.key}>'


class AIConfig(SingletonModel, TimestampedModel):
    """Singleton with the active AI provider configuration.

    A single row (pk=1). Admin picks provider + model, pastes the API key,
    and `core.services.ai.*` use it automatically. If disabled or keyless,
    AI features return 501 and forms work without AI assistance.
    """
    provider = models.CharField(
        max_length=20, choices=AIProvider.choices, default=AIProvider.CLAUDE,
        verbose_name='AI provider',
    )
    model = models.CharField(
        max_length=80, blank=True, default='claude-haiku-4-5-20251001',
        verbose_name='Model',
        help_text='Model identifier per provider (e.g. claude-haiku-4-5-20251001).',
    )
    api_key = EncryptedCharField(
        max_length=1000, blank=True, default='',
        help_text='Encrypted at rest with Fernet. Only readable from Python (not SQL).',
    )
    temperature = models.FloatField(
        default=0.7, help_text='0.0 = deterministic, 1.0 = creative.',
    )
    max_tokens = models.PositiveIntegerField(
        default=1024, help_text='Max tokens in the response.',
    )
    system_prompt_override = models.TextField(
        blank=True, default='',
        verbose_name='Global system prompt (optional)',
        help_text='If set, prepended to all system prompts.',
    )
    enabled = models.BooleanField(
        default=False,
        help_text='If off, all AI features are disabled.',
    )

    class Meta:
        verbose_name = 'AI Configuration'
        verbose_name_plural = 'AI Configuration'

    def __str__(self) -> str:
        return f'AIConfig<{self.provider}:{self.model} {"ON" if self.enabled else "OFF"}>'

    def is_ready(self) -> bool:
        """True if enabled and has an api_key."""
        return self.enabled and bool(self.api_key) and bool(self.model)

    def masked_api_key(self) -> str:
        """API key masked except the last 4 chars."""
        if not self.api_key:
            return ''
        if len(self.api_key) <= 8:
            return '••••••••'
        return f'{self.api_key[:4]}••••••••{self.api_key[-4:]}'
