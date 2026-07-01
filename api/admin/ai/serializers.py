from rest_framework import serializers

from core.models import AIConfig, PROVIDER_MODELS


class AIConfigSerializer(serializers.ModelSerializer):
    """Lectura/escritura de la config IA. La api_key se enmascara en lectura."""
    api_key = serializers.SerializerMethodField()
    api_key_input = serializers.CharField(write_only=True, required=False, allow_blank=True)
    provider_label = serializers.CharField(source='get_provider_display', read_only=True)
    available_models = serializers.SerializerMethodField()
    is_ready = serializers.BooleanField(read_only=True)

    class Meta:
        model = AIConfig
        fields = [
            'provider', 'provider_label', 'model', 'api_key', 'api_key_input',
            'temperature', 'max_tokens', 'system_prompt_override',
            'enabled', 'is_ready', 'available_models',
        ]

    def get_api_key(self, obj):
        return obj.masked_api_key()

    def get_available_models(self, obj):
        return {
            provider: [{'id': mid, 'label': lbl} for mid, lbl in models]
            for provider, models in PROVIDER_MODELS.items()
        }

    def update(self, instance, validated_data):
        # Si el admin manda api_key_input no vacía, la guardamos.
        new_key = validated_data.pop('api_key_input', None)
        if new_key is not None and new_key.strip():
            instance.api_key = new_key.strip()
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class AITestInputSerializer(serializers.Serializer):
    """Permite probar la config con valores del form antes de guardar."""
    prompt = serializers.CharField(default='Decí "hola" en una palabra.', required=False)
    # Overrides opcionales — si vienen, se usan en vez de leer la DB
    provider = serializers.CharField(required=False, allow_blank=True)
    model = serializers.CharField(required=False, allow_blank=True)
    api_key = serializers.CharField(required=False, allow_blank=True)
    temperature = serializers.FloatField(required=False)
    max_tokens = serializers.IntegerField(required=False)


class CopilotBodyInputSerializer(serializers.Serializer):
    tipo_evento = serializers.ChoiceField(
        choices=['seminario', 'taller', 'curso', 'conferencia', 'capacitacion'],
        default='seminario',
    )
    contexto = serializers.CharField(required=False, allow_blank=True, default='')
    tono = serializers.ChoiceField(
        choices=['formal', 'amigable', 'inspirador', 'corto', 'expandido'],
        default='formal',
    )
    accion = serializers.ChoiceField(
        choices=['create', 'rewrite', 'shorten', 'expand'],
        default='create',
    )


class ExcelMapInputSerializer(serializers.Serializer):
    sample_data = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField(allow_blank=True)),
        help_text='Dict: {columna: [valores de muestra]}',
    )


class VoiceExtractInputSerializer(serializers.Serializer):
    transcripcion = serializers.CharField(
        help_text='Texto transcrito del audio del admin',
        min_length=5,
    )


class EventBannerInputSerializer(serializers.Serializer):
    """Generación de banner con IA. Requiere el título; prompt es ajustable."""
    titulo = serializers.CharField(min_length=3, max_length=200)
    prompt = serializers.CharField(required=False, allow_blank=True, default='')


class EventDescriptionInputSerializer(serializers.Serializer):
    """Asistente IA para descripción de evento. Requiere al menos el título."""
    titulo = serializers.CharField(min_length=3, max_length=200)
    accion = serializers.ChoiceField(
        choices=['create', 'improve', 'expand', 'shorten', 'formal', 'friendly'],
        default='create',
    )
    contexto = serializers.CharField(required=False, allow_blank=True, default='')
    descripcion_actual = serializers.CharField(required=False, allow_blank=True, default='')
