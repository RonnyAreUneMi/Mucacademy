"""Tests del módulo de evaluación: modelo, intentos, submit y calificaciones."""
import pytest
from django.core.exceptions import ValidationError

from core.models import (
    Program, Evaluation, Question, EvaluationAttempt, EvaluationGrant,
)
from tests.factories import EventFactory, ParticipantFactory


@pytest.fixture
def program_eval(db):
    program = Program.objects.create(name='Prog Eval')
    ev = Evaluation.objects.create(program=program, pass_threshold=60, max_attempts=2)
    Question.objects.create(evaluation=ev, text='2+2', kind='mcq', options=['3', '4', '5', '6'], correct_idx=1)
    Question.objects.create(evaluation=ev, text='El sol es una estrella', kind='boolean', options=['Verdadero', 'Falso'], correct_idx=0)
    return ev


@pytest.mark.django_db
class TestEvaluationModel:
    def test_owner_must_be_exactly_one(self):
        program = Program.objects.create(name='P')
        event = EventFactory()
        ev = Evaluation(program=program, event=event)
        with pytest.raises(ValidationError):
            ev.clean()

    def test_attempts_and_grant(self, program_eval):
        p = ParticipantFactory()
        ev = program_eval
        assert ev.attempts_allowed_for(p) == 2
        assert ev.can_attempt(p) is True
        EvaluationAttempt.objects.create(evaluation=ev, participant=p, correct=1, total=2, score=50, passed=False, submitted_at=_now())
        EvaluationAttempt.objects.create(evaluation=ev, participant=p, correct=1, total=2, score=50, passed=False, submitted_at=_now())
        assert ev.attempts_used_by(p) == 2
        assert ev.can_attempt(p) is False
        EvaluationGrant.objects.create(evaluation=ev, participant=p, extra_attempts=1)
        assert ev.attempts_allowed_for(p) == 3
        assert ev.can_attempt(p) is True

    def test_passed_by_uses_best(self, program_eval):
        p = ParticipantFactory()
        ev = program_eval
        EvaluationAttempt.objects.create(evaluation=ev, participant=p, correct=1, total=2, score=50, passed=False, submitted_at=_now())
        assert ev.passed_by(p) is False
        EvaluationAttempt.objects.create(evaluation=ev, participant=p, correct=2, total=2, score=100, passed=True, submitted_at=_now())
        assert ev.passed_by(p) is True


@pytest.mark.django_db
class TestPublicSubmit:
    def _client_for(self, participant):
        from rest_framework.test import APIClient
        from core.models import ParticipantToken
        token = ParticipantToken.generate_for(participant, days=1)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        return c

    def test_submit_grades_and_limits(self, program_eval):
        from core.models import Attendance
        ev = program_eval
        p = ParticipantFactory()
        p.set_password('x'); p.save()
        # Debe haber asistido a un seminario del programa para "acceder".
        course = ev.program.active_courses.first() or EventFactory(program=ev.program)
        Attendance.objects.create(event=course, participant=p)

        c = self._client_for(p)
        qs = list(ev.active_questions)
        answers = {str(qs[0].id): 1, str(qs[1].id): 0}  # ambas correctas
        r = c.post(f'/api/v1/public/account/evaluations/{ev.id}/submit/', {'answers': answers}, format='json')
        assert r.status_code == 200
        assert r.data['score'] == 100.0
        assert r.data['passed'] is True
        assert r.data['correct'] == 2

        # Segundo intento (fallado) y luego bloqueo por límite.
        c.post(f'/api/v1/public/account/evaluations/{ev.id}/submit/', {'answers': {str(qs[0].id): 0, str(qs[1].id): 1}}, format='json')
        r3 = c.post(f'/api/v1/public/account/evaluations/{ev.id}/submit/', {'answers': answers}, format='json')
        assert r3.status_code == 403  # sin intentos


def _now():
    from django.utils import timezone
    return timezone.now()
