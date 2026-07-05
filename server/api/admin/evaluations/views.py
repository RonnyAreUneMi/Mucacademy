from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import Evaluation, Question, EvaluationGrant, Participant
from core.models.evaluations import QuestionSource
from api.common.viewsets import AuditedModelViewSet

from .serializers import (
    EvaluationSerializer, EvaluationListSerializer, QuestionSerializer,
)


class EvaluationViewSet(AuditedModelViewSet):
    """CRUD de evaluaciones + banco de preguntas, generación IA y calificaciones."""
    queryset = Evaluation.objects.select_related('program', 'event').all()
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['program', 'event', 'is_active']
    ordering = ['-created_at']
    audit_verbose_name = 'evaluación'

    def get_serializer_class(self):
        if self.action == 'list':
            return EvaluationListSerializer
        return EvaluationSerializer

    @action(detail=True, methods=['post'], url_path='generate-questions')
    def generate_questions(self, request, pk=None):
        """POST {count?, sources?} → genera preguntas con IA y las agrega al banco.

        sources: lista opcional de fuentes ['summary','document','title'] (mixto).
        """
        evaluation = self.get_object()
        count = int(request.data.get('count', 10) or 10)
        count = max(1, min(count, 30))
        sources = request.data.get('sources') or None
        if isinstance(sources, str):
            sources = [s.strip() for s in sources.split(',') if s.strip()]

        from core.services.ai.question_bank import generate_questions as ai_generate
        try:
            items = ai_generate(evaluation, count=count, sources=sources)
        except NotImplementedError:
            return Response(
                {'error': 'IA no configurada. Actívala en /panel/ai/config/.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response({'error': f'No se pudo generar: {e}'}, status=status.HTTP_502_BAD_GATEWAY)

        base_order = (evaluation.questions.count())
        created = []
        for i, q in enumerate(items):
            created.append(Question.objects.create(
                evaluation=evaluation,
                text=q['text'], kind=q['kind'], options=q['options'],
                correct_idx=q['correct_idx'], explanation=q.get('explanation', ''),
                source=QuestionSource.AI, order=base_order + i,
            ))
        self.log_audit('CREATE', f'Evaluación {evaluation.id}: {len(created)} preguntas IA')
        return Response(
            {'created': len(created), 'questions': QuestionSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'])
    def gradebook(self, request, pk=None):
        """Registro de calificaciones: por participante, mejor nota, intentos y estado."""
        evaluation = self.get_object()
        rows = {}
        attempts = (
            evaluation.attempts.filter(submitted_at__isnull=False)
            .select_related('participant').order_by('participant_id', '-score')
        )
        for a in attempts:
            p = a.participant
            row = rows.get(p.id)
            if row is None:
                rows[p.id] = {
                    'participant_id': p.id,
                    'name': f'{p.first_name} {p.last_name}'.strip(),
                    'email': p.email,
                    'best_score': round(a.score, 1),
                    'passed': a.passed,
                    'attempts_used': 1,
                    'attempts_allowed': evaluation.attempts_allowed_for(p),
                }
            else:
                row['attempts_used'] += 1
                if a.score > row['best_score']:
                    row['best_score'] = round(a.score, 1)
                    row['passed'] = row['passed'] or a.passed
        data = sorted(rows.values(), key=lambda r: (-r['best_score'], r['name']))
        return Response({
            'pass_threshold': evaluation.pass_threshold,
            'total_questions': evaluation.question_count,
            'rows': data,
        })

    @action(detail=True, methods=['post'], url_path='grant-attempt')
    def grant_attempt(self, request, pk=None):
        """POST {participant_id, extra?, reason?} → intentos extra para un participante."""
        evaluation = self.get_object()
        pid = request.data.get('participant_id')
        participant = Participant.objects.filter(pk=pid).first()
        if participant is None:
            return Response({'error': 'Participante no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        extra = max(1, int(request.data.get('extra', 1) or 1))
        grant, _ = EvaluationGrant.objects.get_or_create(
            evaluation=evaluation, participant=participant,
            defaults={'granted_by': request.user},
        )
        grant.extra_attempts += extra
        grant.reason = request.data.get('reason', grant.reason)
        grant.granted_by = request.user
        grant.save()
        self.log_audit('UPDATE', f'Evaluación {evaluation.id}: +{extra} intentos a {participant}')
        return Response({
            'ok': True,
            'participant_id': participant.id,
            'extra_attempts': grant.extra_attempts,
            'attempts_allowed': evaluation.attempts_allowed_for(participant),
        })


class QuestionViewSet(AuditedModelViewSet):
    """CRUD de preguntas del banco (agregar/editar/borrar manualmente)."""
    queryset = Question.objects.all()
    permission_classes = [permissions.IsAdminUser]
    serializer_class = QuestionSerializer
    filterset_fields = ['evaluation', 'is_active', 'kind']
    ordering = ['order', 'id']
    audit_verbose_name = 'pregunta'

    def perform_create(self, serializer):
        serializer.save(source=QuestionSource.MANUAL)
