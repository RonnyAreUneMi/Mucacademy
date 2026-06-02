from rest_framework import serializers

from core.models import Certificate


class CertificadoListSerializer(serializers.ModelSerializer):
    lote_nombre = serializers.CharField(source='batch.name', read_only=True)
    lote_facultad = serializers.CharField(source='batch.faculty', read_only=True)
    lote_facultad_display = serializers.CharField(source='batch.get_faculty_display', read_only=True)
    participante_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            'id', 'verification_hash', 'national_id', 'first_name', 'last_name',
            'email', 'course', 'course_date', 'hours',
            'batch', 'lote_nombre', 'lote_facultad', 'lote_facultad_display',
            'participant', 'participante_nombre',
            'download_count', 'search_count', 'last_download_at',
            'created_at',
        ]
        read_only_fields = ('verification_hash', 'download_count', 'search_count',
                            'last_download_at', 'created_at')

    def get_participante_nombre(self, obj):
        p = obj.participant
        return f'{p.first_name} {p.last_name}' if p else ''


class CertificadoDetailSerializer(CertificadoListSerializer):
    class Meta(CertificadoListSerializer.Meta):
        pass


class CertificadoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = [
            'batch', 'participant', 'national_id', 'first_name', 'last_name',
            'email', 'phone', 'course', 'course_date', 'hours',
        ]
