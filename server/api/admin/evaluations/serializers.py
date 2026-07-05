from rest_framework import serializers

from core.models import Evaluation, Question


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            'id', 'evaluation', 'text', 'kind', 'options', 'correct_idx',
            'explanation', 'points', 'source', 'order', 'is_active',
        ]
        read_only_fields = ('source',)

    def validate(self, attrs):
        options = attrs.get('options', getattr(self.instance, 'options', []) or [])
        ci = attrs.get('correct_idx', getattr(self.instance, 'correct_idx', 0))
        if not isinstance(options, list) or len(options) < 2:
            raise serializers.ValidationError({'options': 'Debe tener al menos 2 opciones.'})
        if not 0 <= ci < len(options):
            raise serializers.ValidationError({'correct_idx': 'Índice de respuesta fuera de rango.'})
        return attrs


class EvaluationSerializer(serializers.ModelSerializer):
    owner_label = serializers.CharField(read_only=True)
    question_count = serializers.IntegerField(read_only=True)
    questions = QuestionSerializer(source='active_questions', many=True, read_only=True)
    document_name = serializers.SerializerMethodField()

    class Meta:
        model = Evaluation
        fields = [
            'id', 'program', 'event', 'owner_label', 'title', 'description',
            'pass_threshold', 'max_attempts', 'questions_per_attempt',
            'shuffle_questions', 'is_active', 'question_count', 'questions',
            'document', 'document_name', 'created_at',
        ]
        read_only_fields = ('created_at',)

    def get_document_name(self, obj):
        try:
            return obj.document.name.split('/')[-1] if obj.document else ''
        except Exception:
            return ''

    def validate(self, attrs):
        program = attrs.get('program', getattr(self.instance, 'program', None))
        event = attrs.get('event', getattr(self.instance, 'event', None))
        if bool(program) == bool(event):
            raise serializers.ValidationError(
                'La evaluación debe pertenecer a un programa O a un seminario (uno solo).'
            )
        return attrs


class EvaluationListSerializer(serializers.ModelSerializer):
    owner_label = serializers.CharField(read_only=True)
    question_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Evaluation
        fields = [
            'id', 'program', 'event', 'owner_label', 'title',
            'pass_threshold', 'max_attempts', 'is_active', 'question_count',
        ]
