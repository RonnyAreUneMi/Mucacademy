"""Tests del certificado de programa: completitud (asistencia+eval) y PDF."""
import pytest
from django.utils import timezone

from core.models import Program, Certificate, Attendance, Evaluation, EvaluationAttempt
from core.models.catalogs.enums import CertificateKind
from core.services import programs as program_service
from tests.factories import EventFactory, ParticipantFactory


def _course(program, hours, skills):
    return EventFactory(program=program, hours=hours, skills=skills)


def _attend(event, participant):
    return Attendance.objects.create(event=event, participant=participant)


@pytest.mark.django_db
class TestProgramIssuance:
    def test_not_complete_until_evaluations_passed(self):
        # Con acceso por inscripción, la finalización ya NO exige asistencia:
        # depende de aprobar la evaluación de cada seminario que tenga una.
        program = Program.objects.create(name='Analítica de Datos')
        p = ParticipantFactory()
        c1 = _course(program, 20, ['SQL joins'])
        _course(program, 16, ['DAX'])
        Evaluation.objects.create(event=c1, pass_threshold=60)  # sin aprobar
        assert program_service.participant_completed_program(program, p) is False
        assert program_service.check_and_issue(program, p) is None

    def test_complete_when_attended_all_and_no_eval(self):
        program = Program.objects.create(name='Analítica de Datos')
        p = ParticipantFactory()
        c1 = _course(program, 20, ['SQL joins', 'Modelado'])
        c2 = _course(program, 16, ['DAX', 'Dashboards'])
        _attend(c1, p); _attend(c2, p)

        assert program_service.participant_completed_program(program, p) is True
        cert = program_service.check_and_issue(program, p)
        assert cert is not None
        assert cert.is_program is True
        assert cert.hours == 36
        assert len(cert.program_data) == 2

    def test_eval_required_when_present(self):
        program = Program.objects.create(name='Programa con eval')
        p = ParticipantFactory()
        c1 = _course(program, 10, ['a'])
        c2 = _course(program, 10, ['b'])
        _attend(c1, p); _attend(c2, p)
        ev = Evaluation.objects.create(program=program, pass_threshold=60)

        # Asistió a todo pero no aprobó la evaluación → no completa.
        assert program_service.participant_completed_program(program, p) is False
        EvaluationAttempt.objects.create(
            evaluation=ev, participant=p, correct=1, total=2, score=50, passed=False,
            submitted_at=timezone.now(),
        )
        assert program_service.participant_completed_program(program, p) is False
        EvaluationAttempt.objects.create(
            evaluation=ev, participant=p, correct=2, total=2, score=100, passed=True,
            submitted_at=timezone.now(),
        )
        assert program_service.participant_completed_program(program, p) is True

    def test_issuance_is_idempotent(self):
        program = Program.objects.create(name='Programa X')
        p = ParticipantFactory()
        c1 = _course(program, 10, ['a']); c2 = _course(program, 10, ['b'])
        _attend(c1, p); _attend(c2, p)

        first = program_service.check_and_issue(program, p)
        second = program_service.check_and_issue(program, p)
        assert first is not None
        assert second is None
        n = Certificate.objects.filter(participant=p, batch__kind=CertificateKind.PROGRAM).count()
        assert n == 1

    def test_program_pdf_renders(self):
        program = Program.objects.create(name='Programa PDF')
        p = ParticipantFactory()
        c1 = _course(program, 20, ['SQL', 'Índices']); c2 = _course(program, 15, ['Power BI'])
        _attend(c1, p); _attend(c2, p)
        cert = program_service.check_and_issue(program, p)

        from core.services.pdf import generate_certificate_pdf
        data = generate_certificate_pdf(cert).getvalue()
        assert data[:4] == b'%PDF'
        assert len(data) > 1000
