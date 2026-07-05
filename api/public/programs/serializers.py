"""Serializers públicos de programas (participante / mobile / web)."""
from rest_framework import serializers

from core.models import Program, Event


def _abs_url(request, filefield):
    if filefield and hasattr(filefield, 'url'):
        url = filefield.url
        return request.build_absolute_uri(url) if request else url
    return None


class PublicProgramSeminarSerializer(serializers.ModelSerializer):
    """Un seminario del programa: descripción, imagen, horas, habilidad y nota mínima."""
    banner_url = serializers.SerializerMethodField()
    skill = serializers.SerializerMethodField()
    min_grade = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'hours', 'date', 'modality',
                  'banner_url', 'skill', 'min_grade']

    def get_banner_url(self, obj):
        return _abs_url(self.context.get('request'), obj.banner_image)

    def get_skill(self, obj):
        skills = obj.skills or []
        return skills[0] if skills else None

    def get_min_grade(self, obj):
        ev = getattr(obj, 'evaluation', None)
        return ev.pass_threshold if (ev and ev.is_active) else None


class PublicProgramListSerializer(serializers.ModelSerializer):
    banner_url = serializers.SerializerMethodField()
    course_count = serializers.IntegerField(read_only=True)
    total_hours = serializers.IntegerField(read_only=True)

    class Meta:
        model = Program
        fields = ['id', 'name', 'description', 'faculty', 'banner_url',
                  'course_count', 'total_hours']

    def get_banner_url(self, obj):
        return _abs_url(self.context.get('request'), obj.banner_image)


class PublicProgramDetailSerializer(PublicProgramListSerializer):
    seminars = serializers.SerializerMethodField()
    min_grade = serializers.SerializerMethodField()

    class Meta(PublicProgramListSerializer.Meta):
        fields = PublicProgramListSerializer.Meta.fields + ['seminars', 'min_grade']

    def get_seminars(self, obj):
        return PublicProgramSeminarSerializer(
            obj.active_courses, many=True, context=self.context
        ).data

    def get_min_grade(self, obj):
        """Nota mínima del programa = la más alta exigida entre sus seminarios."""
        grades = []
        for course in obj.active_courses:
            ev = getattr(course, 'evaluation', None)
            if ev and ev.is_active:
                grades.append(ev.pass_threshold)
        return max(grades) if grades else None
