from rest_framework import serializers

from core.models import Participant, Certificate


class CertificadoMiniSerializer(serializers.ModelSerializer):
    lote_nombre = serializers.CharField(source='batch.name', read_only=True)

    class Meta:
        model = Certificate
        fields = ['id', 'verification_hash', 'course', 'course_date', 'hours', 'lote_nombre']


class ParticipanteListSerializer(serializers.ModelSerializer):
    certificados_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Participant
        fields = [
            'id', 'national_id', 'first_name', 'last_name', 'email', 'phone',
            'is_leader', 'certificados_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ('created_at', 'updated_at')


class ParticipanteDetailSerializer(ParticipanteListSerializer):
    certificates = CertificadoMiniSerializer(many=True, read_only=True)

    class Meta(ParticipanteListSerializer.Meta):
        fields = ParticipanteListSerializer.Meta.fields + ['certificates']


class ParticipanteWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields = ['national_id', 'first_name', 'last_name', 'email', 'phone', 'is_leader']

    def validate(self, attrs):
        national_id = attrs.get('national_id', '') or (self.instance and self.instance.national_id) or ''
        email = attrs.get('email', '') or (self.instance and self.instance.email) or ''
        if not national_id and not email:
            raise serializers.ValidationError('Debe proporcionar al menos cédula o correo.')
        return attrs
