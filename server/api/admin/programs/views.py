from rest_framework import permissions, status
from api.admin.permissions import IsPanelAdmin
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import Program, Certificate
from core.models.catalogs.enums import CertificateKind
from core.services import programs as program_service
from api.common.viewsets import AuditedModelViewSet

from .serializers import ProgramSerializer, ProgramListSerializer


class ProgramViewSet(AuditedModelViewSet):
    """CRUD admin de programas académicos (agrupan varios cursos)."""
    queryset = Program.objects.all()
    permission_classes = [IsPanelAdmin]
    filterset_fields = ['is_active', 'faculty']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    audit_verbose_name = 'programa'

    def get_serializer_class(self):
        if self.action == 'list':
            return ProgramListSerializer
        return ProgramSerializer

    def audit_detail(self, instance, action):
        return f'Programa #{instance.pk} ({instance.name})'

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Progreso por participante: cuántos cursos completó y si ya tiene el cert de programa."""
        program = self.get_object()
        courses = list(program.active_courses)
        batch_ids = [c.batch_id for c in courses if c.batch_id]

        # Certificados de curso emitidos dentro de este programa
        course_certs = (
            Certificate.objects
            .filter(batch_id__in=batch_ids, participant__isnull=False)
            .select_related('participant')
        )
        # Certificados de programa ya emitidos
        program_batch = program.batches.filter(kind=CertificateKind.PROGRAM).first()
        program_cert_pids = set()
        if program_batch:
            program_cert_pids = set(
                Certificate.objects.filter(batch=program_batch, participant__isnull=False)
                .values_list('participant_id', flat=True)
            )

        by_participant = {}
        for cert in course_certs:
            p = cert.participant
            row = by_participant.setdefault(p.id, {
                'participant_id': p.id,
                'name': f'{p.first_name} {p.last_name}'.strip(),
                'email': p.email,
                'courses_done': 0,
                'has_program_cert': p.id in program_cert_pids,
            })
            row['courses_done'] += 1

        total_courses = len(courses)
        rows = sorted(by_participant.values(), key=lambda r: (-r['courses_done'], r['name']))
        return Response({
            'total_courses': total_courses,
            'participants': rows,
        })

    @action(detail=True, methods=['post'], url_path='issue-certificates')
    def issue_certificates(self, request, pk=None):
        """Emite manualmente el cert de programa a quienes ya completaron todos los cursos."""
        program = self.get_object()
        courses = list(program.active_courses)
        batch_ids = [c.batch_id for c in courses if c.batch_id]
        candidate_pids = set(
            Certificate.objects.filter(batch_id__in=batch_ids, participant__isnull=False)
            .values_list('participant_id', flat=True)
        )

        from core.models import Participant
        from core.services.email import sender as email_sender

        issued = 0
        for participant in Participant.objects.filter(id__in=candidate_pids):
            cert = program_service.check_and_issue(program, participant, administrator=request.user)
            if cert is None:
                continue
            issued += 1
            try:
                email_sender.send_program_certificate_issued(
                    certificado=cert, program=program, participante=participant, request=request,
                )
            except Exception:
                pass

        self.log_audit('CREATE', f'Programa {program.id}: {issued} certificados de programa emitidos')
        return Response({'ok': True, 'issued': issued}, status=status.HTTP_200_OK)
