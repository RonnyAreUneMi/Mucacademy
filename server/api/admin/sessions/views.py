import os
import uuid
from datetime import datetime
from io import BytesIO

from django.conf import settings as django_settings
from django.core.files import File
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import (
    Event, Enrollment, Attendance,
    CertificateBatch, Certificate, Signature,
)
from core.models.catalogs.enums import EventModality
from core.services.pdf_service import generate_certificate_pdf
from core.services.meet import calendar_client as meet_calendar
from core.tasks.email_tasks import send_certificate_issued_bulk
from api.common.viewsets import AuditedModelViewSet

from .serializers import (
    SesionListSerializer,
    SesionDetailSerializer,
    SesionWriteSerializer,
    ConfirmacionSerializer,
)


class SesionViewSet(AuditedModelViewSet):
    """CRUD admin de sesiones/eventos."""
    queryset = Event.objects.all()
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['is_active', 'modality', 'leaders_only', 'date', 'batch']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['date', 'start_time', 'created_at']
    ordering = ['-date', '-start_time']

    audit_verbose_name = 'sesion'

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return SesionWriteSerializer
        if self.action == 'retrieve':
            return SesionDetailSerializer
        return SesionListSerializer

    def audit_detail(self, instance, action):
        return f'Sesión #{instance.pk} ({instance.title or instance.day_of_week} - {instance.date})'

    # ── Hooks Google Calendar / Meet ─────────────────────────────
    def _should_auto_create_meet(self, sesion: Event) -> bool:
        """Toda sesión virtual = Meet auto-generado (no hay otras plataformas)."""
        return (
            sesion.modality == EventModality.VIRTUAL
            and not sesion.google_calendar_event_id
        )

    def perform_create(self, serializer):
        sesion = serializer.save()
        if self._should_auto_create_meet(sesion):
            result = meet_calendar.create_meet_event(sesion)
            if result is not None:
                meet_link, event_id = result
                sesion.meeting_url = meet_link
                sesion.google_calendar_event_id = event_id
                sesion.save(update_fields=['meeting_url', 'google_calendar_event_id'])
                self.log_audit('CREATE', f'Meet event #{sesion.pk}: {meet_link}')
        # Auditoría base (la del AuditedModelViewSet)
        self.log_audit(self._action_code('create'), self.audit_detail(sesion, 'create'))

    def perform_update(self, serializer):
        sesion = serializer.save()
        # Si tiene evento de Calendar y cambió fecha/hora, sincronizamos.
        if sesion.google_calendar_event_id:
            meet_calendar.update_meet_event(sesion)
        # Si recién ahora se marcó como virtual+meet, creamos el evento.
        elif self._should_auto_create_meet(sesion):
            result = meet_calendar.create_meet_event(sesion)
            if result is not None:
                meet_link, event_id = result
                sesion.meeting_url = meet_link
                sesion.google_calendar_event_id = event_id
                sesion.save(update_fields=['meeting_url', 'google_calendar_event_id'])
        self.log_audit(self._action_code('update'), self.audit_detail(sesion, 'update'))

    def destroy(self, request, *args, **kwargs):
        sesion = self.get_object()
        force = request.query_params.get('force') in ('1', 'true', 'True')
        n_enroll = sesion.enrollments.count()
        n_att = sesion.attendances.count()
        # Sin `force`: si tiene participantes pedimos confirmación extra.
        if (n_enroll or n_att) and not force:
            return Response(
                {
                    'error': 'Este evento tiene participantes.',
                    'needs_confirm': True,
                    'enrollments': n_enroll,
                    'attendances': n_att,
                },
                status=status.HTTP_409_CONFLICT,
            )
        # Con `force` (o sin participantes): se borra en cascada (las
        # inscripciones y asistencias se eliminan automáticamente por FK CASCADE).
        if sesion.google_calendar_event_id:
            meet_calendar.delete_meet_event(sesion.google_calendar_event_id)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='suggest-skills')
    def suggest_skills(self, request):
        """POST {title, description, event_id?} → lista de competencias sugeridas por IA.

        Funciona para eventos nuevos (sin id, usa title/description) o existentes
        (con event_id, aprovecha además el resumen del evento).
        """
        from core.services.ai.skills import suggest_skills_for_event

        event_id = request.data.get('event_id')
        if event_id:
            event = Event.objects.filter(pk=event_id).first()
            if event is None:
                return Response({'error': 'Evento no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Objeto ligero para eventos aún no guardados
            event = Event(
                title=request.data.get('title', ''),
                description=request.data.get('description', ''),
            )
        try:
            skills = suggest_skills_for_event(event)
        except NotImplementedError:
            return Response(
                {'error': 'IA no configurada. Actívala en /panel/ai/config/.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:  # errores del proveedor de IA
            return Response({'error': f'No se pudo generar: {e}'}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'skills': skills})

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        sesion = self.get_object()
        sesion.is_active = not sesion.is_active
        sesion.save(update_fields=['is_active'])
        self.log_audit('UPDATE', f'Event #{sesion.pk} → is_active={sesion.is_active}')
        return Response({'id': sesion.id, 'is_active': sesion.is_active})

    @action(detail=True, methods=['get'])
    def confirmados(self, request, pk=None):
        sesion = self.get_object()
        qs = (
            Enrollment.objects
            .filter(event=sesion, confirmed=True)
            .select_related('participant')
            .order_by('-enrolled_at')
        )
        return Response(ConfirmacionSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'])
    def attendees(self, request, pk=None):
        """GET ?since=... → feed de asistencias en tiempo real."""
        sesion = self.get_object()
        since_str = request.query_params.get('since', '')

        registros = Attendance.objects.filter(event=sesion).select_related('participant', 'certificate')

        if since_str:
            try:
                since_dt = datetime.fromisoformat(since_str)
                registros = registros.filter(registered_at__gt=since_dt)
            except (ValueError, TypeError):
                pass

        registros = registros.order_by('-registered_at')[:50]
        total = Attendance.objects.filter(event=sesion).count()

        attendees = []
        for r in registros:
            p = r.participant
            c = r.certificate
            # Convertir a hora local antes de formatear (la BDD guarda UTC)
            local_dt = timezone.localtime(r.registered_at)
            attendees.append({
                'id': r.id,
                'nombre': f'{p.first_name} {p.last_name}' if p else (f'{c.first_name} {c.last_name}' if c else '?'),
                'cedula': p.national_id if p else (c.national_id if c else ''),
                'email': p.email if p else (c.email if c else ''),
                'hora': local_dt.strftime('%H:%M:%S'),
                'timestamp': r.registered_at.isoformat(),
            })

        return Response({
            'total': total,
            'attendees': attendees,
            'server_time': timezone.now().isoformat(),
        })

    @action(detail=True, methods=['get'], url_path='qr-info')
    def qr_info(self, request, pk=None):
        """GET → URL de check-in absoluta + totales para la pantalla QR."""
        sesion = self.get_object()
        checkin_url = request.build_absolute_uri(f'/checkin/{sesion.qr_code}/')
        return Response({
            'codigo_qr': sesion.qr_code,
            'checkin_url': checkin_url,
            'total_registros': Attendance.objects.filter(event=sesion).count(),
            'titulo': sesion.title or sesion.day_of_week,
            'fecha': sesion.date.strftime('%d/%m/%Y'),
            'horario': sesion.label,
        })

    @action(detail=True, methods=['get'], url_path='bulk-pdf')
    def bulk_pdf(self, request, pk=None):
        """GET → merge PDF de todos los certificados de participantes confirmados."""
        from PyPDF2 import PdfMerger

        sesion = self.get_object()
        confirmaciones = Enrollment.objects.filter(
            event=sesion, confirmed=True
        ).select_related('certificate', 'certificate__batch')

        if not confirmaciones.exists():
            return Response({'error': 'No hay participantes confirmados.'}, status=status.HTTP_404_NOT_FOUND)

        merger = PdfMerger()
        count = 0
        for conf in confirmaciones:
            try:
                cert = conf.certificate
                if not cert:
                    continue
                pdf_buffer = generate_certificate_pdf(cert)
                merger.append(pdf_buffer)
                count += 1
            except Exception:
                continue

        if count == 0:
            return Response({'error': 'No se pudo generar ningún certificado.'}, status=status.HTTP_404_NOT_FOUND)

        output_buffer = BytesIO()
        merger.write(output_buffer)
        merger.close()
        output_buffer.seek(0)

        safe_dia = sesion.day_of_week.replace('é', 'e').replace('á', 'a')
        filename = f'Certificados_{safe_dia}_{sesion.start_time:%H%M}_{count}personas.pdf'

        self.log_audit('DOWNLOAD', f'Event #{sesion.pk}: {count} PDFs merged')
        response = HttpResponse(output_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['post'], url_path='generate-batch')
    def generate_batch(self, request, pk=None):
        """POST {facultad} → crea CertificateBatch desde los confirmados de esta sesión."""
        sesion = self.get_object()

        if sesion.batch:
            return Response(
                {'error': 'Esta sesión ya tiene un lote asociado.', 'lote_id': sesion.batch_id},
                status=status.HTTP_409_CONFLICT,
            )

        confirmaciones = list(
            Enrollment.objects.filter(
                event=sesion, confirmed=True, participant__isnull=False
            ).select_related('participant')
        )

        if not confirmaciones:
            return Response(
                {'error': 'No hay participantes confirmados para generar certificados.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Si el evento exige aprobar el quiz, filtramos a los que aprobaron.
        excluidos = 0
        if sesion.certificate_requires_quiz:
            aprobados = [c for c in confirmaciones if sesion.quiz_passed_by(c.participant)]
            excluidos = len(confirmaciones) - len(aprobados)
            confirmaciones = aprobados
            if not confirmaciones:
                return Response(
                    {'error': (
                        f'Ningún participante aprobó el cuestionario '
                        f'(mínimo {sesion.quiz_pass_threshold}%). No se generaron certificados.'
                    )},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        facultad = request.data.get('faculty', request.data.get('facultad', 'FACI'))

        with transaction.atomic():
            sesion = Event.objects.select_for_update().get(pk=pk)
            if sesion.batch:
                return Response(
                    {'error': 'Esta sesión ya tiene un lote asociado.', 'lote_id': sesion.batch_id},
                    status=status.HTTP_409_CONFLICT,
                )

            lote = CertificateBatch.objects.create(
                name=sesion.title or f'Sesión {sesion.date} {sesion.label}',
                administrator=request.user,
                faculty=facultad,
            )

            # Si el seminario pertenece a un programa, hereda el diseño del
            # certificado del programa (mismo para todos sus seminarios). Suelto = default.
            applied = False
            if sesion.program_id:
                from core.services import programs as program_service
                applied = program_service.apply_program_design(sesion.program, lote)
            if not applied:
                firmas_default = list(Signature.objects.filter(is_active=True).order_by('sort_order')[:3])
                for i, firma in enumerate(firmas_default, start=1):
                    setattr(lote, f'signature_inst_{i}', firma)
            # Sin logos hardcodeados: los logos salen del Diseño Global / config del lote.
            lote.save()

            certs = []
            for conf in confirmaciones:
                p = conf.participant
                certs.append(Certificate(
                    batch=lote,
                    participant=p,
                    national_id=p.national_id or f'GEN-{uuid.uuid4().hex[:8].upper()}',
                    first_name=p.first_name,
                    last_name=p.last_name,
                    email=p.email,
                    phone=p.phone,
                    course=lote.name.upper(),
                    course_date=sesion.date,
                    hours=sesion.hours or 0,
                ))
            Certificate.objects.bulk_create(certs)

            sesion.batch = lote
            sesion.save(update_fields=['batch'])

        self.log_audit(
            'CREATE',
            f'Batch "{lote.name}" generated from event {sesion.id} with {len(certs)} certificates',
        )

        # ── Notificación por correo a cada participante (async vía Celery) ──
        # En vez de bloquear el request mientras se envían N correos, despachamos
        # una task de Celery que itera y envía. En desarrollo sin Redis, EAGER
        # mode hace que corra inmediatamente sincrónica (mismo comportamiento).
        send_certificate_issued_bulk.delay(batch_id=lote.id)

        # Si el curso pertenece a un programa, revisamos (async) qué
        # participantes completaron TODOS los cursos → cert de programa.
        if sesion.program_id:
            from core.tasks.program_tasks import issue_program_certificates_for_event
            issue_program_certificates_for_event.delay(event_id=sesion.id)

        return Response({
            'ok': True,
            'batch_id': lote.id,
            'batch_name': lote.name,
            'certificates_created': len(certs),
            'emails_queued': len(certs),
            'excluded_no_quiz': excluidos,
        })
