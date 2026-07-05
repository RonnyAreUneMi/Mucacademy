from django.db import transaction
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response

from api.public.account.authentication import ParticipanteTokenAuthentication

from core.models import (
    Event, Participant, Enrollment, Certificate,
    SessionSummary, QuizAttempt, Attendance,
)

from .resumen_serializers import ResumenSesionSerializer, IntentoCuestionarioSerializer
from .serializers import SesionListSerializer, SesionDetailSerializer
from .utils import sesion_payload


class PublicSesionViewSet(viewsets.ReadOnlyModelViewSet):
    """Endpoint público: listar eventos activos e inscribirse."""
    queryset = Event.objects.active().select_related('batch')
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['modality']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['date', 'start_time']
    ordering = ['date', 'start_time']

    def get_serializer_class(self):
        return SesionDetailSerializer if self.action == 'retrieve' else SesionListSerializer

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        qs = Event.objects.upcoming().select_related('batch')
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    @action(detail=False, methods=['get'])
    def past(self, request):
        qs = Event.objects.past().select_related('batch')[:50]
        return Response(self.get_serializer(qs, many=True).data)

    # ── Inscripción pública ─────────────────────────────────────

    @action(detail=True, methods=['get'], url_path='search-participant')
    def search_participant(self, request, pk=None):
        sesion = self.get_object()
        query = request.query_params.get('q', '').strip()
        if len(query) < 3:
            return Response({'found': False, 'results': []})

        tokens = query.split()
        q_filter = Q(national_id__icontains=query) | Q(email__icontains=query)
        for t in tokens:
            q_filter |= Q(first_name__icontains=t) | Q(last_name__icontains=t)
        participantes = list(Participant.objects.filter(q_filter).distinct()[:15])

        if not participantes:
            return Response({'found': False, 'results': []})

        def _data(p):
            ya = Enrollment.objects.filter(
                participant=p, event=sesion, confirmed=True
            ).exists()
            q_cursos = Q(participant=p)
            if p.national_id:
                q_cursos |= Q(national_id__iexact=p.national_id)
            if p.email:
                q_cursos |= Q(email__iexact=p.email)
            cursos = list(
                Certificate.objects.filter(q_cursos)
                .values_list('batch__name', flat=True).distinct()[:10]
            )
            missing = []
            for field in ('national_id', 'email', 'first_name', 'last_name'):
                if not getattr(p, field):
                    missing.append(field)
            return {
                'id': p.id, 'cedula': p.national_id, 'email': p.email,
                'nombres': p.first_name, 'apellidos': p.last_name,
                'celular': p.phone or '',
                'cursos': [c for c in cursos if c],
                'missing_info': missing, 'ya_confirmado': ya,
            }

        if len(participantes) == 1:
            p = participantes[0]
            return Response({
                'found': True, 'count': 1,
                'participante': _data(p),
                'ya_confirmado': Enrollment.objects.filter(
                    participant=p, event=sesion, confirmed=True
                ).exists(),
            })

        return Response({
            'found': True, 'count': len(participantes),
            'results': [_data(p) for p in participantes],
        })

    @action(detail=True, methods=['post'], url_path='confirm-participant')
    def confirm_participant(self, request, pk=None):
        sesion = self.get_object()
        pid = request.data.get('participante_id')
        if not pid:
            return Response({'ok': False, 'error': 'Datos incompletos.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            p = Participant.objects.get(id=pid)
        except Participant.DoesNotExist:
            return Response({'ok': False, 'error': 'Participante no encontrado.'},
                            status=status.HTTP_404_NOT_FOUND)

        if sesion.leaders_only and not p.is_leader:
            return Response({'ok': False, 'error': 'Este evento es exclusivo para Líderes Académicos.'},
                            status=status.HTTP_403_FORBIDDEN)

        fields = []
        for req_name, attr_name in (
            ('celular', 'phone'), ('email', 'email'), ('cedula', 'national_id'),
            ('nombres', 'first_name'), ('apellidos', 'last_name'),
        ):
            val = (request.data.get(req_name) or '').strip()
            if not val:
                continue
            current = getattr(p, attr_name)
            if req_name in ('celular', 'email'):
                if val != current:
                    setattr(p, attr_name, val)
                    fields.append(attr_name)
            elif not current:
                setattr(p, attr_name, val)
                fields.append(attr_name)
        if fields:
            p.save(update_fields=fields)

        if sesion.is_full:
            return Response({'ok': False, 'error': 'Este evento ya alcanzó el cupo máximo.'},
                            status=status.HTTP_409_CONFLICT)

        conf, created = Enrollment.objects.get_or_create(
            participant=p, event=sesion, defaults={'confirmed': True}
        )
        if not created:
            return Response({'ok': True, 'already': True, 'message': 'Ya estás registrado en este evento.'})

        return Response({
            'ok': True, 'already': False,
            'message': f'Registro exitoso para {p.first_name}.',
            'sesion': sesion_payload(sesion),
        })

    # ── Resumen IA del transcript (Drive → IA → Markdown) ─────────

    @action(
        detail=True, methods=['get'], url_path='resumen',
        authentication_classes=[ParticipanteTokenAuthentication, SessionAuthentication],
        permission_classes=[permissions.AllowAny],  # endpoint público (read-only)
    )
    def resumen(self, request, pk=None):
        """Devuelve el SessionSummary + grabación + intentos del participante.

        Si el request viene autenticado con ParticipantToken, también incluye:
          - intentos: lista de QuizAttempt del participante
          - mejor_intento: el con mayor `correct`
          - intentos_disponibles: int (MAX_ATTEMPTS - usados)
          - asistio: bool
          - inscrito: bool
          - recording: { name, web_link } o null

        Estados:
          - 200 + payload → resumen disponible
          - 200 + {estado: 'no_existe'} → evento válido pero sin resumen aún
          - 404 → evento no existe
        """
        sesion = self.get_object()
        resumen = SessionSummary.objects.filter(event=sesion).first()

        # Datos del participante (si viene autenticado)
        participante = None
        principal = getattr(request, 'user', None)
        if principal is not None and getattr(principal, 'is_authenticated', False):
            participante = getattr(principal, 'participant', None)

        intentos_data = []
        mejor_intento = None
        intentos_disponibles = QuizAttempt.MAX_ATTEMPTS
        asistio = False
        inscrito = False
        if participante is not None:
            intentos = list(QuizAttempt.objects.filter(participant=participante, event=sesion))
            intentos_data = IntentoCuestionarioSerializer(intentos, many=True).data
            if intentos:
                mejor = max(intentos, key=lambda x: x.correct)
                mejor_intento = IntentoCuestionarioSerializer(mejor).data
            intentos_disponibles = max(0, QuizAttempt.MAX_ATTEMPTS - len(intentos))
            asistio = Attendance.objects.filter(participant=participante, event=sesion).exists()
            inscrito = Enrollment.objects.filter(participant=participante, event=sesion).exists()

        # Grabación de Drive (lazy, solo si resumen READY)
        recording = None
        if resumen and resumen.status == 'ready':
            try:
                from core.services.meet.drive_client import find_recording_for_session
                rec = find_recording_for_session(sesion)
                if rec:
                    recording = {
                        'file_id': rec.file_id,
                        'name': rec.name,
                        'web_link': rec.web_link,
                    }
            except Exception:
                recording = None

        if resumen is None:
            return Response({
                'estado': 'no_existe',
                'message': 'Este evento todavía no tiene resumen IA generado.',
                'transcripcion_habilitada': sesion.transcription_enabled,
                'intentos': intentos_data,
                'intentos_disponibles': intentos_disponibles,
                'mejor_intento': mejor_intento,
                'max_intentos': QuizAttempt.MAX_ATTEMPTS,
                'recording': None,
                'asistio': asistio,
                'inscrito': inscrito,
            })
        ser = ResumenSesionSerializer(resumen)
        payload = dict(ser.data)
        # Si el evento no usa quiz, no exponemos preguntas.
        if not sesion.quiz_enabled:
            payload['quiz'] = []
        aprobado = sesion.quiz_passed_by(participante) if participante else False
        return Response({
            **payload,
            'intentos': intentos_data,
            'mejor_intento': mejor_intento,
            'intentos_disponibles': intentos_disponibles,
            'max_intentos': QuizAttempt.MAX_ATTEMPTS,
            'recording': recording,
            'asistio': asistio,
            'inscrito': inscrito,
            # Config de evaluación / certificado
            'quiz_habilitado': sesion.quiz_enabled,
            'requiere_quiz_certificado': sesion.certificate_requires_quiz,
            'nota_minima': sesion.quiz_pass_threshold,
            'aprobado': aprobado,
            'certificado_desbloqueado': sesion.certificate_unlocked_for(participante) if participante else False,
        })

    @action(
        detail=True, methods=['get'], url_path='resumen/pdf',
        authentication_classes=[ParticipanteTokenAuthentication, SessionAuthentication],
        permission_classes=[permissions.IsAuthenticated],
    )
    def resumen_pdf(self, request, pk=None):
        """Devuelve el PDF del resumen IA — autenticado con ParticipantToken.

        Diferencia con la versión web (`/cuenta/eventos/<id>/resumen/pdf/`):
        esta acepta el header `Authorization: Token <key>` que envía el
        mobile, así no requiere sesión Django. Devuelve el PDF como bytes
        con Content-Type apropiado para que el cliente lo guarde y comparta.
        """
        from django.http import HttpResponse
        from django.utils.text import slugify
        from core.services.pdf.resumen_pdf import generar_resumen_pdf

        sesion = self.get_object()
        participante = getattr(request.user, 'participant', None)
        if participante is None:
            return Response({'ok': False, 'error': 'Auth requerida.'}, status=status.HTTP_401_UNAUTHORIZED)

        inscrito = Enrollment.objects.filter(participant=participante, event=sesion).exists()
        asistio  = Attendance.objects.filter(participant=participante, event=sesion).exists()
        if not (inscrito or asistio):
            return Response({'ok': False, 'error': 'Sin acceso al resumen.'}, status=status.HTTP_403_FORBIDDEN)

        resumen = SessionSummary.objects.filter(event=sesion).first()
        if not resumen or resumen.status != 'ready':
            return Response({'ok': False, 'error': 'El resumen aún no está listo.'}, status=status.HTTP_400_BAD_REQUEST)

        pdf_bytes = generar_resumen_pdf(resumen)
        titulo_slug = slugify(sesion.title or sesion.day_of_week or 'evento')[:50] or 'resumen'
        fecha_slug = sesion.date.strftime('%Y-%m-%d') if sesion.date else 'sf'
        filename = f'Resumen-Betto-{titulo_slug}-{fecha_slug}.pdf'

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf_bytes)
        return response

    @action(
        detail=True, methods=['post'], url_path='cuestionario/submit',
        authentication_classes=[ParticipanteTokenAuthentication, SessionAuthentication],
        permission_classes=[permissions.IsAuthenticated],
    )
    def submit_cuestionario(self, request, pk=None):
        """Registra un intento del cuestionario para el participante autenticado.

        Body: { respuestas: [int|null], tiempo_total_seg: int }
        Devuelve: { ok, intento, intentos_restantes }
        """
        sesion = self.get_object()
        participante = getattr(request.user, 'participant', None)
        if participante is None:
            return Response({'ok': False, 'error': 'Auth requerida.'}, status=status.HTTP_401_UNAUTHORIZED)

        inscrito = Enrollment.objects.filter(participant=participante, event=sesion).exists()
        asistio  = Attendance.objects.filter(participant=participante, event=sesion).exists()
        if not (inscrito or asistio):
            return Response({'ok': False, 'error': 'Sin acceso al cuestionario.'}, status=status.HTTP_403_FORBIDDEN)

        if not sesion.quiz_enabled:
            return Response({'ok': False, 'error': 'Este evento no tiene cuestionario.'}, status=status.HTTP_400_BAD_REQUEST)

        resumen = SessionSummary.objects.filter(event=sesion).first()
        if not resumen or resumen.status != 'ready' or not resumen.quiz:
            return Response({'ok': False, 'error': 'Cuestionario no disponible.'}, status=status.HTTP_400_BAD_REQUEST)

        intentos_count = QuizAttempt.objects.filter(participant=participante, event=sesion).count()
        if intentos_count >= QuizAttempt.MAX_ATTEMPTS:
            return Response({
                'ok': False,
                'error': f'Ya alcanzaste el máximo de {QuizAttempt.MAX_ATTEMPTS} intentos.',
            }, status=status.HTTP_409_CONFLICT)

        respuestas = request.data.get('respuestas') or []
        tiempo_total = int(request.data.get('tiempo_total_seg') or 0)

        preguntas = resumen.quiz
        total = len(preguntas)
        correctas = 0
        for i, q in enumerate(preguntas):
            if i < len(respuestas) and respuestas[i] is not None:
                if respuestas[i] == q.get('correct_idx'):
                    correctas += 1

        intento = QuizAttempt.objects.create(
            participant=participante,
            event=sesion,
            correct=correctas,
            total=total,
            total_time_seconds=tiempo_total,
            answers=respuestas,
        )
        porcentaje = round(correctas / total * 100) if total else 0
        aprobado = porcentaje >= sesion.quiz_pass_threshold
        return Response({
            'ok': True,
            'intento': IntentoCuestionarioSerializer(intento).data,
            'intentos_restantes': QuizAttempt.MAX_ATTEMPTS - (intentos_count + 1),
            'porcentaje': porcentaje,
            'nota_minima': sesion.quiz_pass_threshold,
            'aprobado': aprobado,
            'requiere_quiz_certificado': sesion.certificate_requires_quiz,
        }, status=status.HTTP_201_CREATED)

    @action(
        detail=True, methods=['post'], url_path='resumen/procesar',
        authentication_classes=[ParticipanteTokenAuthentication, SessionAuthentication],
        permission_classes=[permissions.IsAuthenticated],
    )
    def procesar_resumen(self, request, pk=None):
        """Dispara el procesamiento IA en background (Celery task).

        Requiere autenticación: token de participante o sesión de admin Django.
        Esto evita que cualquier visitante sin auth queme tokens IA gratis.
        """
        from core.tasks.transcript_tasks import process_event_transcript

        sesion = self.get_object()
        if not sesion.transcription_enabled:
            return Response(
                {'ok': False, 'error': 'La transcripción IA está deshabilitada para este evento.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        process_event_transcript.delay(sesion.id)
        return Response(
            {'ok': True, 'message': 'Procesamiento encolado.', 'sesion_id': sesion.id},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=['post'], url_path='register-participant')
    def register_participant(self, request, pk=None):
        sesion = self.get_object()
        cedula = (request.data.get('cedula') or '').strip().upper()
        nombres = (request.data.get('nombres') or '').strip().upper()
        apellidos = (request.data.get('apellidos') or '').strip().upper()
        email = (request.data.get('email') or '').strip().lower()
        celular = (request.data.get('celular') or '').strip()

        if not nombres or not apellidos:
            return Response({'ok': False, 'error': 'Nombres y apellidos son obligatorios.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not cedula and not email:
            return Response({'ok': False, 'error': 'Debe proporcionar al menos cédula o correo.'},
                            status=status.HTTP_400_BAD_REQUEST)

        p = None
        if cedula:
            p = Participant.objects.filter(national_id=cedula).first()
        if not p and email:
            p = Participant.objects.filter(email__iexact=email).first()

        if sesion.leaders_only and (not p or not p.is_leader):
            return Response({'ok': False, 'error': 'Este evento es exclusivo para Líderes Académicos.'},
                            status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            if p:
                fields = []
                if celular and not p.phone:
                    p.phone = celular; fields.append('phone')
                if cedula and not p.national_id:
                    p.national_id = cedula; fields.append('national_id')
                if email and not p.email:
                    p.email = email; fields.append('email')
                if fields:
                    p.save(update_fields=fields)
            else:
                p = Participant.objects.create(
                    national_id=cedula, first_name=nombres, last_name=apellidos,
                    email=email, phone=celular,
                )

            if sesion.is_full:
                return Response({'ok': False, 'error': 'Este evento ya alcanzó el cupo máximo.'},
                                status=status.HTTP_409_CONFLICT)

            conf, created = Enrollment.objects.get_or_create(
                participant=p, event=sesion, defaults={'confirmed': True}
            )

        if not created:
            return Response({'ok': True, 'already': True, 'message': 'Ya estás registrado en este evento.'})

        return Response({
            'ok': True, 'already': False,
            'message': f'Registro exitoso para {p.first_name} {p.last_name}.',
            'participante': {'id': p.id, 'nombres': p.first_name, 'apellidos': p.last_name},
            'sesion': sesion_payload(sesion),
        })
