"""Serializers del API de cuenta pública (mobile)."""
from rest_framework import serializers

from core.models import Certificate, Participant, Event


class LoginInputSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)


class RegisterInputSerializer(serializers.Serializer):
    nombres   = serializers.CharField(max_length=100)
    apellidos = serializers.CharField(max_length=100)
    email     = serializers.EmailField()
    cedula    = serializers.CharField(required=False, allow_blank=True, default='')
    celular   = serializers.CharField(required=False, allow_blank=True, default='')
    password  = serializers.CharField(write_only=True, min_length=6)


class ParticipanteSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(source='full_name', read_only=True)
    initials        = serializers.CharField(read_only=True)
    avatar_url      = serializers.SerializerMethodField()

    class Meta:
        model = Participant
        fields = [
            'id', 'first_name', 'last_name', 'email', 'national_id', 'phone',
            'is_leader', 'nombre_completo', 'initials', 'avatar_url',
            'last_login', 'created_at',
        ]
        read_only_fields = fields

    def get_avatar_url(self, obj):
        return obj.avatar.url if obj.avatar else None


class CertificadoSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    verify_url   = serializers.SerializerMethodField()
    lote_nombre  = serializers.CharField(source='batch.name', read_only=True)
    is_program   = serializers.BooleanField(read_only=True)

    class Meta:
        model = Certificate
        fields = [
            'id', 'course', 'course_date', 'hours',
            'verification_hash', 'lote_nombre',
            'is_program',
            'download_url', 'verify_url',
            'created_at',
        ]
        read_only_fields = fields

    def get_download_url(self, obj):
        return f'/api/v1/public/certificates/{obj.verification_hash}/download/'

    def get_verify_url(self, obj):
        return f'/verificar/{obj.verification_hash}/'


class SesionMobileSerializer(serializers.ModelSerializer):
    es_virtual    = serializers.BooleanField(source='is_virtual', read_only=True)
    titulo_display = serializers.SerializerMethodField()
    banner_url    = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'titulo_display', 'description',
            'date', 'day_of_week', 'start_time', 'end_time',
            'modality', 'es_virtual', 'meeting_url', 'location',
            'banner_url', 'is_active',
        ]
        read_only_fields = fields

    def get_titulo_display(self, obj):
        return obj.title or obj.day_of_week

    def get_banner_url(self, obj):
        return obj.banner_image.url if obj.banner_image else None
