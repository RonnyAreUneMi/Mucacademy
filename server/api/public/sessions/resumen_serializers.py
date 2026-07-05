"""Serializers del módulo "resumen" para el endpoint mobile.

No expone `transcript_raw` (puede ser MUY largo, varios MB) — el cliente
mobile no lo necesita; solo el resumen procesado y el cuestionario.
"""
from rest_framework import serializers

from core.models import QuizAttempt, SessionSummary


class IntentoCuestionarioSerializer(serializers.ModelSerializer):
    porcentaje = serializers.IntegerField(source='percentage', read_only=True)

    class Meta:
        model = QuizAttempt
        fields = [
            'id', 'correct', 'total', 'porcentaje',
            'total_time_seconds', 'answers', 'created_at',
        ]
        read_only_fields = fields


class ResumenSesionSerializer(serializers.ModelSerializer):
    is_ready = serializers.BooleanField(read_only=True)
    has_failed = serializers.BooleanField(read_only=True)
    estado_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SessionSummary
        fields = [
            'id', 'status', 'estado_display',
            'is_ready', 'has_failed',
            'summary_md', 'key_points', 'next_steps', 'quiz',
            'duration_minutes', 'transcript_chars',
            'ai_model', 'created_at', 'processed_at',
        ]
        read_only_fields = fields
