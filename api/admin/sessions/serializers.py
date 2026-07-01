import json

from rest_framework import serializers

from core.models import Event, Enrollment, Attendance, Speaker


class PonenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Speaker
        fields = ['id', 'name', 'title', 'affiliation', 'bio', 'sort_order']


class SesionListSerializer(serializers.ModelSerializer):
    plataforma_display = serializers.CharField(source='platform_display_safe', read_only=True)
    es_virtual = serializers.BooleanField(source='is_virtual', read_only=True)
    confirmados_count = serializers.IntegerField(source='enrolled_count', read_only=True)
    cupos_disponibles = serializers.IntegerField(source='available_seats', read_only=True, allow_null=True)
    esta_llena = serializers.BooleanField(source='is_full', read_only=True)
    imagen_banner_url = serializers.SerializerMethodField()
    lote_nombre = serializers.CharField(source='batch.name', read_only=True, allow_null=True)
    speakers = PonenteSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'imagen_banner_url',
            'modality', 'virtual_platform', 'plataforma_display', 'meeting_url',
            'location', 'date', 'day_of_week', 'start_time', 'end_time',
            'capacity', 'leaders_only', 'is_active', 'qr_code',
            'confirmados_count', 'cupos_disponibles', 'esta_llena',
            'es_virtual', 'batch', 'lote_nombre', 'speakers', 'created_at',
        ]
        read_only_fields = ('qr_code', 'created_at')

    def get_imagen_banner_url(self, obj):
        request = self.context.get('request')
        if obj.banner_image and hasattr(obj.banner_image, 'url'):
            url = obj.banner_image.url
            return request.build_absolute_uri(url) if request else url
        return None


class SesionDetailSerializer(SesionListSerializer):
    class Meta(SesionListSerializer.Meta):
        pass


class SesionWriteSerializer(serializers.ModelSerializer):
    """Serializer de escritura para sesiones. Soporta ponentes anidados.

    El form HTML envía los ponentes como JSON serializado en el campo
    `ponentes_json` (FormData no soporta listas anidadas). Internamente lo
    parseamos y reemplazamos completamente la lista en cada save.
    """
    ponentes_json = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # parent_event como texto para tolerar '' (FormData "sin serie") sin romper el parseo.
    parent_event = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Event
        # `day_of_week` es property derivada de `date` — no se envía en writes
        fields = [
            'title', 'description', 'banner_image',
            'modality', 'virtual_platform', 'meeting_url',
            'location', 'date', 'start_time', 'end_time',
            'capacity', 'leaders_only', 'is_active', 'batch',
            'has_parts',
            'quiz_enabled', 'certificate_requires_quiz', 'quiz_pass_threshold',
            'ponentes_json', 'parent_event',
        ]

    def validate_ponentes_json(self, value: str):
        """Parsea el JSON y valida que sea lista de dicts con `name`."""
        if not value:
            return []
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            raise serializers.ValidationError('Formato JSON inválido en ponentes.')
        if not isinstance(data, list):
            raise serializers.ValidationError('Ponentes debe ser una lista.')
        cleaned = []
        for i, p in enumerate(data):
            if not isinstance(p, dict):
                continue
            name = (p.get('name') or '').strip()
            if not name:
                continue  # silenciosamente saltamos los vacíos
            cleaned.append({
                'name': name,
                'title': (p.get('title') or '').strip(),
                'affiliation': (p.get('affiliation') or '').strip(),
                'bio': (p.get('bio') or '').strip(),
                'sort_order': i,
            })
        return cleaned

    def validate(self, attrs):
        """Sesiones virtuales = siempre Google Meet (auto-generado por Calendar API).

        El admin no escoge plataforma ni enlace: ambos se llenan en el hook
        `perform_create` del viewset. Para presenciales, limpiamos los dos.
        """
        modality = attrs.get('modality') or (self.instance and self.instance.modality)
        if modality == 'virtual':
            attrs['virtual_platform'] = 'meet'
            # enlace lo rellena Calendar API (queda vacío hasta entonces)
        elif modality == 'in_person':
            attrs['meeting_url'] = ''
            attrs['virtual_platform'] = ''

        return attrs

    def _resolve_parent(self, validated_data):
        """Convierte el parent_event (texto) a Event|None y normaliza has_parts.

        Devuelve (parent_event|None, has_parts|None). has_parts None = no tocar.
        """
        if 'parent_event' not in validated_data:
            return None, None  # PATCH parcial sin el campo → no tocar
        raw = (validated_data.pop('parent_event', '') or '').strip()
        has_parts = validated_data.get('has_parts')
        if raw.isdigit():
            parent = Event.objects.filter(pk=int(raw)).first()
            if parent and self.instance and parent.pk == self.instance.pk:
                raise serializers.ValidationError(
                    {'parent_event': 'Un evento no puede ser continuación de sí mismo.'}
                )
            return parent, True  # continuación → siempre es parte de una serie
        # Sin parent: respeta el has_parts que vino (primera parte vs normal)
        return None, has_parts

    def _save_ponentes(self, event, ponentes_data):
        """Reemplaza la lista de ponentes de la sesión."""
        event.speakers.all().delete()
        Speaker.objects.bulk_create([
            Speaker(event=event, **p) for p in ponentes_data
        ])

    def _apply_series(self, validated_data):
        """Resuelve parent_event (texto→Event|None) y ajusta has_parts en validated_data."""
        had_field = 'parent_event' in validated_data
        parent, has_parts = self._resolve_parent(validated_data)
        if had_field:
            validated_data['parent_event'] = parent
            if has_parts is not None:
                validated_data['has_parts'] = has_parts

    def create(self, validated_data):
        ponentes_data = validated_data.pop('ponentes_json', None)
        self._apply_series(validated_data)
        event = super().create(validated_data)
        if ponentes_data is not None:
            self._save_ponentes(event, ponentes_data)
        return event

    def update(self, instance, validated_data):
        ponentes_data = validated_data.pop('ponentes_json', None)
        self._apply_series(validated_data)
        event = super().update(instance, validated_data)
        if ponentes_data is not None:
            self._save_ponentes(event, ponentes_data)
        return event


class ConfirmacionSerializer(serializers.ModelSerializer):
    participante_nombre = serializers.SerializerMethodField()
    participante_email = serializers.CharField(source='participant.email', read_only=True)
    participante_cedula = serializers.CharField(source='participant.national_id', read_only=True)
    ya_asistio = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            'id', 'participant', 'participante_nombre',
            'participante_email', 'participante_cedula',
            'confirmed', 'enrolled_at', 'ya_asistio',
        ]
        read_only_fields = fields

    def get_participante_nombre(self, obj):
        p = obj.participant
        return f'{p.first_name} {p.last_name}' if p else ''

    def get_ya_asistio(self, obj):
        return Attendance.objects.filter(
            event=obj.event, participant=obj.participant
        ).exists()
