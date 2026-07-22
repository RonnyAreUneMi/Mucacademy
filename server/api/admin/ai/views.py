from rest_framework import permissions, status
from api.admin.permissions import HasModulePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from core.base.mixins import log_audit
from core.models import AIConfig
from core.services.ai import banner, copilot, excel_mapper, insights, recommender, voice
from core.services.ai import client as ai_client

from .serializers import (
    AIConfigSerializer,
    AITestInputSerializer,
    CopilotBodyInputSerializer,
    EventBannerInputSerializer,
    EventDescriptionInputSerializer,
    ExcelMapInputSerializer,
    VoiceExtractInputSerializer,
)


class BaseAIView(APIView):
    """Base para endpoints de IA. Auditan uso."""
    permission_classes = [HasModulePermission]
    ai_action = ''

    def _respond(self, result: dict):
        """Si la feature no está implementada → 501 Not Implemented."""
        if not result.get('implemented', False):
            return Response(result, status=status.HTTP_501_NOT_IMPLEMENTED)
        return Response(result)

    def _audit(self, detail: str):
        log_audit(self.request.user, f'IA_{self.ai_action}', detail)


class CopilotBodyView(BaseAIView):
    """POST: genera cuerpo de certificado con IA."""
    ai_action = 'COPILOT_BODY'

    def post(self, request):
        ser = CopilotBodyInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = copilot.generate_body_text(**ser.validated_data)
        self._audit(f'tipo={ser.validated_data["tipo_evento"]} tono={ser.validated_data["tono"]}')
        return self._respond(result)


class EventDescriptionView(BaseAIView):
    """POST: asistente IA para la descripción de un evento.

    Recibe: titulo (req), accion, contexto (prompt libre), descripcion_actual.
    Devuelve: HTML enriquecido para CKEditor.
    """
    ai_action = 'EVENT_DESCRIPTION'

    def post(self, request):
        ser = EventDescriptionInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = copilot.improve_event_description(**ser.validated_data)
        self._audit(
            f'accion={ser.validated_data["accion"]} '
            f'titulo={ser.validated_data["titulo"][:60]!r}'
        )
        if not result.get('implemented'):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response({'ok': True, 'html': result['html'], 'action': result.get('action')})


class EventBannerView(BaseAIView):
    """POST: genera un banner de evento con IA + branding fijo UNEMI.

    Recibe: titulo (req), prompt (ajustable, opcional).
    Devuelve: image_base64 (data URL PNG) listo para previsualizar y subir.
    """
    ai_action = 'EVENT_BANNER'

    def post(self, request):
        ser = EventBannerInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        titulo = ser.validated_data['titulo']
        prompt = ser.validated_data.get('prompt', '')
        try:
            result = banner.generate_event_banner(titulo, prompt)
        except NotImplementedError as exc:
            return Response({'ok': False, 'error': str(exc)},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001 — mostramos el error real al admin
            return Response({'ok': False, 'error': f'{type(exc).__name__}: {exc}'},
                            status=status.HTTP_502_BAD_GATEWAY)
        self._audit(f'titulo={titulo[:60]!r}')
        return Response({
            'ok': True,
            'image_base64': result['image_base64'],
            'prompt': result['prompt'],
            'filename': result['filename'],
        })


class ExcelMapColumnsView(BaseAIView):
    """POST: clasifica columnas de Excel con IA."""
    ai_action = 'EXCEL_MAP'

    def post(self, request):
        ser = ExcelMapInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = excel_mapper.map_excel_columns(ser.validated_data['sample_data'])
        cols = list(ser.validated_data['sample_data'].keys())
        self._audit(f'mapping {len(cols)} cols: {cols[:5]}')
        return self._respond(result)


class VoiceExtractView(BaseAIView):
    """POST: extrae entidades de sesión desde voz transcrita."""
    ai_action = 'VOICE_EXTRACT'

    def post(self, request):
        ser = VoiceExtractInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = voice.extract_entities_from_voice(ser.validated_data['transcripcion'])
        self._audit(f'len={len(ser.validated_data["transcripcion"])}')
        return self._respond(result)


class InsightsDashboardView(BaseAIView):
    """GET: insights narrativos del dashboard."""
    ai_action = 'INSIGHTS'

    def get(self, request):
        result = insights.generate_insights()
        self._audit('dashboard insights')
        return self._respond(result)


class RecommendationsView(APIView):
    """GET: recomendaciones para un email. Público (post-inscripción)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, email):
        result = recommender.recommend_for_email(email)
        if not result.get('implemented', False):
            return Response(result, status=status.HTTP_501_NOT_IMPLEMENTED)
        return Response(result)


# ── Configuración IA (singleton) ──────────────────────────────

class AIConfigView(APIView):
    """GET / PUT: leer y actualizar la config IA singleton."""
    permission_classes = [HasModulePermission]

    def _get_or_create(self) -> AIConfig:
        cfg, _ = AIConfig.objects.get_or_create(pk=1)
        return cfg

    def get(self, request):
        cfg = self._get_or_create()
        return Response(AIConfigSerializer(cfg).data)

    def put(self, request):
        cfg = self._get_or_create()
        ser = AIConfigSerializer(cfg, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        log_audit(request.user, 'AI_CONFIG_UPDATE',
                  f'provider={cfg.provider} model={cfg.model} enabled={cfg.enabled}')
        return Response(AIConfigSerializer(cfg).data)


class AIProvidersView(APIView):
    """GET/PUT: credenciales por proveedor (con orden de fallback) + params globales."""
    permission_classes = [HasModulePermission]

    def _available_models(self):
        from core.models import PROVIDER_MODELS
        return {
            provider: [{'id': mid, 'label': lbl} for mid, lbl in models]
            for provider, models in PROVIDER_MODELS.items()
        }

    def get(self, request):
        from core.models import AIConfig, AIProviderCredential, AIProvider
        cfg, _ = AIConfig.objects.get_or_create(pk=1)
        existing = {c.provider: c for c in AIProviderCredential.objects.all()}
        providers = []
        for value, label in AIProvider.choices:
            c = existing.get(value)
            providers.append({
                'provider': value,
                'provider_label': label,
                'model': c.model if c else '',
                'enabled': c.enabled if c else False,
                'priority': c.priority if c else 100,
                'has_key': bool(c.api_key) if c else False,
                'api_key_masked': c.masked_api_key() if c else '',
            })
        providers.sort(key=lambda p: p['priority'])
        return Response({
            'enabled': cfg.enabled,
            'temperature': cfg.temperature,
            'max_tokens': cfg.max_tokens,
            'system_prompt_override': cfg.system_prompt_override,
            'available_models': self._available_models(),
            'providers': providers,
        })

    def put(self, request):
        from core.models import AIConfig, AIProviderCredential, AIProvider
        data = request.data or {}
        cfg, _ = AIConfig.objects.get_or_create(pk=1)
        # Params globales + master switch.
        if 'enabled' in data:
            cfg.enabled = bool(data['enabled'])
        if 'temperature' in data:
            cfg.temperature = float(data['temperature'])
        if 'max_tokens' in data:
            cfg.max_tokens = int(data['max_tokens'])
        if 'system_prompt_override' in data:
            cfg.system_prompt_override = data['system_prompt_override'] or ''
        cfg.save()

        valid = {v for v, _ in AIProvider.choices}
        for row in data.get('providers', []):
            provider = row.get('provider')
            if provider not in valid:
                continue
            cred, _ = AIProviderCredential.objects.get_or_create(provider=provider)
            if 'model' in row:
                cred.model = (row.get('model') or '').strip()
            if 'enabled' in row:
                cred.enabled = bool(row['enabled'])
            if 'priority' in row:
                try:
                    cred.priority = int(row['priority'])
                except (TypeError, ValueError):
                    pass
            new_key = (row.get('api_key_input') or '').strip()
            if new_key:
                cred.api_key = new_key
            cred.save()

        log_audit(request.user, 'AI_PROVIDERS_UPDATE',
                  f'enabled={cfg.enabled} providers={len(data.get("providers", []))}')
        return self.get(request)


class AIPromptsView(APIView):
    """GET/PUT: prompts editables por feature (override de BD sobre defaults)."""
    permission_classes = [HasModulePermission]

    def get(self, request):
        from core.models import AIPrompt
        from core.services.ai.prompts import REGISTRY, default_prompt
        overrides = {p.key: p.content for p in AIPrompt.objects.all()}
        prompts = []
        for key, meta in REGISTRY.items():
            content = (overrides.get(key) or '').strip()
            prompts.append({
                'key': key,
                'label': meta['label'],
                'description': meta['description'],
                'default': meta['default'],
                'content': content,                       # override ('' = usa default)
                'effective': content or default_prompt(key),
                'is_custom': bool(content),
            })
        return Response({'prompts': prompts})

    def put(self, request):
        from core.models import AIPrompt
        from core.services.ai.prompts import REGISTRY
        for row in (request.data or {}).get('prompts', []):
            key = row.get('key')
            if key not in REGISTRY:
                continue
            content = (row.get('content') or '').strip()
            if content:
                AIPrompt.objects.update_or_create(key=key, defaults={'content': content})
            else:
                # Vacío = restaurar por defecto → borramos el override.
                AIPrompt.objects.filter(key=key).delete()
        log_audit(request.user, 'AI_PROMPTS_UPDATE', 'prompts actualizados')
        return self.get(request)


class AITestView(APIView):
    """POST: prueba la config con overrides opcionales del form (sin persistir).

    Si el form manda `api_key`, `provider`, etc., construye un AIRuntime
    transitorio. Útil para probar antes de guardar.
    """
    permission_classes = [HasModulePermission]

    def post(self, request):
        ser = AITestInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        prompt = data['prompt']

        # Si llegan overrides del form, usamos un runtime transitorio.
        api_key = (data.get('api_key') or '').strip()
        if api_key:
            rt = ai_client.AIRuntime(
                provider=data.get('provider') or 'claude',
                model=data.get('model') or 'claude-haiku-4-5',
                api_key=api_key,
                temperature=data.get('temperature', 0.7),
                max_tokens=data.get('max_tokens', 256),
            )
        else:
            # Sin override → leer de DB. Si la key guardada está vacía,
            # también probamos con la del input (útil cuando el admin
            # solo cambia provider/model sin re-pegar la key).
            rt = ai_client.get_runtime()
            if rt is None:
                # Última chance: usar la key existente en DB aunque enabled=False
                from core.models import AIConfig
                cfg = AIConfig.objects.filter(pk=1).first()
                if cfg and cfg.api_key and cfg.model:
                    rt = ai_client.AIRuntime(
                        provider=data.get('provider') or cfg.provider,
                        model=data.get('model') or cfg.model,
                        api_key=cfg.api_key,
                        temperature=data.get('temperature', cfg.temperature),
                        max_tokens=data.get('max_tokens', cfg.max_tokens),
                    )
            if rt is None:
                return Response(
                    {'ok': False, 'error': 'Falta la API key. Pegala arriba y volvé a probar.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            text = ai_client.call_ai_with_runtime(
                rt,
                system='Sos un asistente que responde en español, breve y directo.',
                user=prompt,
            )
        except RuntimeError as exc:
            return Response({'ok': False, 'error': str(exc)},
                            status=status.HTTP_502_BAD_GATEWAY)
        except Exception as exc:  # noqa: BLE001 — mostramos el error real al admin
            return Response({'ok': False, 'error': f'{type(exc).__name__}: {exc}'},
                            status=status.HTTP_502_BAD_GATEWAY)
        log_audit(request.user, 'AI_CONFIG_TEST', f'provider={rt.provider} model={rt.model}')
        return Response({'ok': True, 'response': text, 'provider': rt.provider, 'model': rt.model})
