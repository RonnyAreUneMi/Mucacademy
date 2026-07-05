from rest_framework import serializers

from core.models import Program, Event


class ProgramCourseSerializer(serializers.ModelSerializer):
    """Curso (evento) resumido para mostrar dentro de un programa."""
    has_batch = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'title', 'date', 'hours', 'skills', 'is_active', 'has_batch']

    def get_has_batch(self, obj):
        return obj.batch_id is not None


class ProgramSerializer(serializers.ModelSerializer):
    course_count = serializers.IntegerField(read_only=True)
    total_hours = serializers.IntegerField(read_only=True)
    courses = ProgramCourseSerializer(source='active_courses', many=True, read_only=True)
    banner_url = serializers.SerializerMethodField()

    class Meta:
        model = Program
        fields = [
            'id', 'name', 'description', 'faculty', 'is_active', 'is_open',
            'certificate_body', 'course_count', 'total_hours',
            'banner_image', 'banner_url',
            'template', 'signature_inst_1', 'signature_inst_2', 'signature_inst_3',
            'courses', 'created_at',
        ]
        read_only_fields = ('created_at',)
        extra_kwargs = {'banner_image': {'write_only': True, 'required': False}}

    def get_banner_url(self, obj):
        request = self.context.get('request')
        if obj.banner_image and hasattr(obj.banner_image, 'url'):
            url = obj.banner_image.url
            return request.build_absolute_uri(url) if request else url
        return None


class ProgramListSerializer(serializers.ModelSerializer):
    """Versión ligera para el listado (sin cursos anidados)."""
    course_count = serializers.IntegerField(read_only=True)
    total_hours = serializers.IntegerField(read_only=True)
    banner_url = serializers.SerializerMethodField()

    class Meta:
        model = Program
        fields = [
            'id', 'name', 'description', 'faculty', 'is_active',
            'course_count', 'total_hours', 'banner_url', 'created_at',
        ]

    def get_banner_url(self, obj):
        request = self.context.get('request')
        if obj.banner_image and hasattr(obj.banner_image, 'url'):
            url = obj.banner_image.url
            return request.build_absolute_uri(url) if request else url
        return None
