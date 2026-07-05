from rest_framework import serializers


class AttendanceSearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    cedula = serializers.CharField(allow_blank=True)
    nombres = serializers.CharField()
    apellidos = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    celular = serializers.CharField(allow_blank=True)
    cursos = serializers.ListField(child=serializers.CharField())
    cursos_count = serializers.IntegerField()


class AttendanceConfirmInputSerializer(serializers.Serializer):
    participante_id = serializers.IntegerField(required=False)
    cert_id = serializers.IntegerField(required=False)
    sesion_id = serializers.IntegerField()

    def validate(self, attrs):
        if not attrs.get('participante_id') and not attrs.get('cert_id'):
            raise serializers.ValidationError('Debe enviar participante_id o cert_id.')
        return attrs


class UpdatePhoneInputSerializer(serializers.Serializer):
    participante_id = serializers.IntegerField(required=False)
    cert_id = serializers.IntegerField(required=False)
    celular = serializers.CharField(allow_blank=True, max_length=20)

    def validate(self, attrs):
        if not attrs.get('participante_id') and not attrs.get('cert_id'):
            raise serializers.ValidationError('Debe enviar participante_id o cert_id.')
        return attrs
