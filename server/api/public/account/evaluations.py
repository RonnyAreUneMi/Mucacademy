"""API pública: el participante rinde la evaluación de un programa/seminario."""
from __future__ import annotations

import random

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Evaluation, Enrollment
from core.services import evaluations as eval_service
from .authentication import ParticipanteTokenAuthentication


class _AuthBase(APIView):
    authentication_classes = [ParticipanteTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_participante(self):
        return self.request.user.participant


def _accessible(participant) -> list:
    """Evaluaciones activas que el participante puede rendir (acceso por inscripción)."""
    enrolled_event_ids = set(
        Enrollment.objects.filter(participant=participant).values_list('event_id', flat=True)
    )
    out = []
    for ev in Evaluation.objects.select_related('program', 'event').filter(is_active=True):
        if ev.program_id:
            course_ids = set(ev.program.active_courses.values_list('id', flat=True))
            if enrolled_event_ids & course_ids:
                out.append(ev)
        elif ev.event_id and ev.event_id in enrolled_event_ids:
            out.append(ev)
    return out


def _serialize_eval(ev, participant, *, with_questions=False):
    best = ev.best_attempt_for(participant)
    data = {
        'id': ev.id,
        'title': ev.title,
        'description': ev.description,
        'owner_label': ev.owner_label,
        'kind': 'program' if ev.program_id else 'event',
        'pass_threshold': ev.pass_threshold,
        'total_questions': ev.question_count,
        'draw_size': ev.draw_size,
        'attempts_allowed': ev.attempts_allowed_for(participant),
        'attempts_used': ev.attempts_used_by(participant),
        'can_attempt': ev.can_attempt(participant) and ev.question_count > 0,
        'best_score': round(best.score, 1) if best else None,
        'passed': ev.passed_by(participant),
    }
    if with_questions:
        questions = list(ev.active_questions)
        if ev.shuffle_questions:
            random.shuffle(questions)
        if ev.draw_size and ev.draw_size < len(questions):
            questions = questions[:ev.draw_size]
        # Sin la respuesta correcta (no filtrar en cliente).
        data['questions'] = [{
            'id': q.id,
            'text': q.text,
            'kind': q.kind,
            'options': q.options,
        } for q in questions]
    return data


class EvaluationsListView(_AuthBase):
    """GET /evaluations/ → evaluaciones que el participante puede rendir."""

    def get(self, request):
        p = self.get_participante()
        evals = _accessible(p)
        return Response({'results': [_serialize_eval(e, p) for e in evals]})


class EvaluationDetailView(_AuthBase):
    """GET /evaluations/<id>/ → info + preguntas (para rendir)."""

    def get(self, request, evaluation_id):
        p = self.get_participante()
        ev = Evaluation.objects.filter(pk=evaluation_id, is_active=True).first()
        if ev is None:
            return Response({'error': 'Evaluación no encontrada.'}, status=404)
        return Response(_serialize_eval(ev, p, with_questions=True))


class EvaluationSubmitView(_AuthBase):
    """POST /evaluations/<id>/submit/ {answers:{question_id: idx}} → califica."""

    def post(self, request, evaluation_id):
        p = self.get_participante()
        ev = Evaluation.objects.filter(pk=evaluation_id, is_active=True).first()
        if ev is None:
            return Response({'error': 'Evaluación no encontrada.'}, status=404)
        if not ev.can_attempt(p):
            return Response(
                {'error': 'No te quedan intentos disponibles.', 'attempts_used': ev.attempts_used_by(p)},
                status=403,
            )

        answers = request.data.get('answers') or {}
        if not isinstance(answers, dict):
            return Response({'error': 'Formato de respuestas inválido.'}, status=400)

        result = eval_service.grade_and_record(ev, p, answers)
        if result is None:
            return Response({'error': 'No se recibieron respuestas válidas.'}, status=400)

        return Response({
            'score': result['score'],
            'correct': result['correct'],
            'total': result['total'],
            'passed': result['passed'],
            'pass_threshold': ev.pass_threshold,
            'attempts_used': ev.attempts_used_by(p),
            'attempts_allowed': ev.attempts_allowed_for(p),
            'detail': result['detail'],
        })
