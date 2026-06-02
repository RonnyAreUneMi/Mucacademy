"""API de cuenta de participante para clientes móviles (Expo)."""
from __future__ import annotations

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import (
    Certificate, Enrollment, Participant, ParticipantToken,
    Attendance, Event,
)

from .authentication import ParticipanteTokenAuthentication
from .serializers import (
    CertificadoSerializer, LoginInputSerializer, ParticipanteSerializer,
    RegisterInputSerializer, SesionMobileSerializer,
)


# ════════════════════════════════════════════════════════════════
#  Auth
# ════════════════════════════════════════════════════════════════

class LoginView(APIView):
    """POST /api/v1/public/account/login/ → token bearer."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = LoginInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data['email'].strip().lower()
        password = ser.validated_data['password']

        try:
            p = Participant.objects.get(email__iexact=email)
        except Participant.DoesNotExist:
            return Response({'error': 'Credenciales inválidas.'}, status=401)
        if not p.has_account or not p.check_password(password):
            return Response({'error': 'Credenciales inválidas.'}, status=401)

        ua = request.META.get('HTTP_USER_AGENT', '')[:255]
        token = ParticipantToken.generate_for(p, days=30, user_agent=ua)
        p.last_login = timezone.now()
        p.save(update_fields=['last_login'])

        return Response({
            'token': token.key,
            'expires_at': token.expires_at.isoformat(),
            'participante': ParticipanteSerializer(p).data,
        })


class RegisterView(APIView):
    """POST /api/v1/public/account/register/ → crea cuenta + token."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = RegisterInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        email = d['email'].strip().lower()

        existing = Participant.objects.filter(email__iexact=email).first()
        if existing and existing.has_account:
            return Response(
                {'error': 'Ya existe una cuenta con ese email. Inicia sesión.'},
                status=409,
            )

        p = existing or Participant(email=email)
        p.first_name = d['nombres'].strip() or p.first_name
        p.last_name  = d['apellidos'].strip() or p.last_name
        if d.get('cedula'):  p.national_id = d['cedula'].strip() or p.national_id
        if d.get('celular'): p.phone = d['celular'].strip() or p.phone
        try:
            p.full_clean(exclude=['password_hash'])
        except Exception as e:
            return Response({'error': str(e)}, status=400)
        p.set_password(d['password'])
        p.save()

        ua = request.META.get('HTTP_USER_AGENT', '')[:255]
        token = ParticipantToken.generate_for(p, days=30, user_agent=ua)
        return Response(
            {
                'token': token.key,
                'expires_at': token.expires_at.isoformat(),
                'participante': ParticipanteSerializer(p).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    """POST /api/v1/public/account/logout/ → invalida el token actual."""
    authentication_classes = [ParticipanteTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # request.auth viene del 2º elemento del tuple devuelto por authenticate()
        token = getattr(request, 'auth', None)
        if isinstance(token, ParticipantToken):
            token.delete()
        return Response({'ok': True})


# ════════════════════════════════════════════════════════════════
#  Landing público (sin auth) — eventos hero + stats
# ════════════════════════════════════════════════════════════════

class LandingView(APIView):
    """GET /api/v1/public/account/landing/ → datos del home antes del login.

    Devuelve los próximos eventos para el carrusel y estadísticas globales
    (total certificados / horas / participantes) para el trust strip.
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        today = timezone.localdate()
        eventos = (Event.objects
            .filter(is_active=True, date__gte=today)
            .order_by('date', 'start_time')[:5])

        agg = Certificate.objects.aggregate(total_horas=Sum('hours'))
        return Response({
            'eventos_hero': SesionMobileSerializer(eventos, many=True).data,
            'stats': {
                'total_certificados': Certificate.objects.count(),
                'total_eventos':      Event.objects.filter(is_active=True).count(),
                'total_horas':        agg['total_horas'] or 0,
                'total_participantes': Participant.objects.count(),
            },
        })


# ════════════════════════════════════════════════════════════════
#  Mi cuenta
# ════════════════════════════════════════════════════════════════

class _AuthenticatedBase(APIView):
    authentication_classes = [ParticipanteTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_participante(self):
        return self.request.user.participant


class MeView(_AuthenticatedBase):
    """GET /api/v1/public/account/me/ → datos del participante autenticado."""

    def get(self, request):
        return Response(ParticipanteSerializer(self.get_participante()).data)


class CertificadosView(_AuthenticatedBase):
    """GET /api/v1/public/account/certificates/ → lista de certificados."""

    def get(self, request):
        p = self.get_participante()
        qs = Certificate.objects.filter(
            Q(national_id=p.national_id) if p.national_id else Q(email__iexact=p.email)
        ).select_related('batch').order_by('-course_date')
        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(course__icontains=q) | Q(batch__name__icontains=q))
        return Response({
            'count': qs.count(),
            'results': CertificadoSerializer(qs, many=True).data,
        })


class EventosView(_AuthenticatedBase):
    """GET /api/v1/public/account/events/?tab=mios|disponibles"""

    def get(self, request):
        from core.models import SessionSummary, ProcessingStatus
        p = self.get_participante()
        tab = request.query_params.get('tab', 'mios')
        today = timezone.localdate()

        confirmados_ids = set(Enrollment.objects.filter(participant=p).values_list('event_id', flat=True))
        asistidos_ids   = set(Attendance.objects.filter(participant=p).values_list('event_id', flat=True))
        mis_ids = confirmados_ids | asistidos_ids

        if tab == 'disponibles':
            eventos = list(Event.objects
                .filter(is_active=True, date__gte=today)
                .exclude(id__in=mis_ids)
                .order_by('date', 'start_time'))
        else:
            eventos = list(Event.objects
                .filter(id__in=mis_ids)
                .order_by('-date', '-start_time'))

        # Eventos con resumen IA listo (para badge "Resumen de Betto")
        ids_eventos = [e.id for e in eventos]
        resumen_listo_ids = set(
            SessionSummary.objects
            .filter(status=ProcessingStatus.READY, event_id__in=ids_eventos)
            .values_list('event_id', flat=True)
        )

        results = []
        for e in eventos:
            data = SesionMobileSerializer(e).data
            if e.id in asistidos_ids:           data['status'] = 'asisti'
            elif e.id in confirmados_ids:
                data['status'] = 'no_asisti' if e.date < today else 'inscrito'
            else:
                data['status'] = 'disponible'
            data['has_resumen'] = e.id in resumen_listo_ids
            results.append(data)

        return Response({
            'tab': tab,
            'count_mios':       len(mis_ids),
            'count_disponibles': Event.objects.filter(is_active=True, date__gte=today).exclude(id__in=mis_ids).count(),
            'results': results,
        })


class EventoDetailView(_AuthenticatedBase):
    """GET /api/v1/public/account/events/<id>/ → detalle de un evento + status del participante.

    Devuelve los campos del evento + el `status` calculado para el usuario actual:
    'asisti' si tiene Attendance, 'inscrito' / 'no_asisti' si se inscribió pero
    no asistió, 'disponible' si nunca se inscribió.
    """

    def get(self, request, event_id: int):
        try:
            sesion = Event.objects.select_related('batch').get(pk=event_id, is_active=True)
        except Event.DoesNotExist:
            return Response({'error': 'Evento no encontrado.'}, status=404)

        p = self.get_participante()
        today = timezone.localdate()

        confirmado = Enrollment.objects.filter(participant=p, event=sesion).exists()
        asistio = Attendance.objects.filter(participant=p, event=sesion).exists()
        if asistio:
            status_value = 'asisti'
        elif confirmado:
            status_value = 'no_asisti' if sesion.date < today else 'inscrito'
        else:
            status_value = 'disponible'

        # Capacidad
        cupos_ocupados = Enrollment.objects.filter(event=sesion).count()

        # Flag de resumen IA listo (para mostrar CTA "Resumen de Betto")
        from core.models import SessionSummary, ProcessingStatus
        has_resumen = SessionSummary.objects.filter(
            event=sesion, status=ProcessingStatus.READY,
        ).exists()

        data = SesionMobileSerializer(sesion).data
        data['status'] = status_value
        data['has_resumen'] = has_resumen
        data['lote_nombre'] = sesion.batch.name if sesion.batch else None
        data['horas'] = getattr(sesion.batch, 'horas_validas', None) if sesion.batch else None
        data['capacidad'] = sesion.capacity
        data['cupos_ocupados'] = cupos_ocupados
        data['cupos_disponibles'] = (
            None if sesion.capacity == 0 else max(0, sesion.capacity - cupos_ocupados)
        )
        return Response(data)


class InscribirEventoView(_AuthenticatedBase):
    """POST /api/v1/public/account/events/<id>/register/ → inscripción 1-click."""

    def post(self, request, event_id: int):
        try:
            sesion = Event.objects.get(pk=event_id, is_active=True)
        except Event.DoesNotExist:
            return Response({'error': 'Evento no disponible.'}, status=404)
        p = self.get_participante()
        _, created = Enrollment.objects.get_or_create(participant=p, event=sesion)
        return Response({'ok': True, 'created': created, 'sesion_id': sesion.id})


class AsistenciasView(_AuthenticatedBase):
    """GET /api/v1/public/account/attendances/ → asistencias del participante.

    Devuelve la lista de eventos donde tiene `Attendance` (asistió de hecho).
    Cada item: id, evento (title, date, hora, modality, location), registered_at local,
    certificado (si ya se emitió uno para ese evento a este participante).
    """

    def get(self, request):
        p = self.get_participante()
        registros = (
            Attendance.objects
            .filter(participant=p)
            .select_related('event', 'event__batch', 'certificate')
            .order_by('-registered_at')
        )

        results = []
        for r in registros:
            s = r.event
            local_dt = timezone.localtime(r.registered_at)
            results.append({
                'id': r.id,
                'sesion_id': s.id,
                'titulo': s.title or s.day_of_week,
                'descripcion': s.description or '',
                'fecha': s.date.strftime('%Y-%m-%d'),
                'dia_semana': s.day_of_week,
                'hora_inicio': s.start_time.strftime('%H:%M'),
                'hora_fin':    s.end_time.strftime('%H:%M'),
                'es_virtual': s.modality == 'virtual',
                'modalidad': s.modality,
                'lugar': s.location or '',
                'lote_nombre': s.batch.name if s.batch else None,
                'fecha_registro': local_dt.strftime('%Y-%m-%d %H:%M'),
                'tiene_certificado': bool(r.certificate_id),
                'certificado_hash': r.certificate.verification_hash if r.certificate else None,
            })

        return Response({
            'count': len(results),
            'results': results,
        })


class CheckinByQRView(_AuthenticatedBase):
    """POST /api/v1/public/account/checkin/ → registra asistencia con QR escaneado.

    Body: { "codigo_qr": "<uuid del QR>" }
    El participante autenticado (vía Token) queda como `Attendance` si:
      - El evento existe y está activo.
      - Es el día del evento (o se permite check-in fuera de día por config).

    Si no existe `Enrollment` previo, lo creamos al vuelo (inscripción
    automática + asistencia).
    """

    def post(self, request):
        codigo_qr = (request.data.get('codigo_qr') or '').strip()
        if not codigo_qr:
            return Response({'error': 'Falta el código QR.'}, status=400)

        # Si vino una URL completa (ej. http://host/checkin/<uuid>/), extraemos el último segmento UUID
        if '/' in codigo_qr:
            parts = [p for p in codigo_qr.rstrip('/').split('/') if p]
            codigo_qr = parts[-1] if parts else codigo_qr

        try:
            sesion = Event.objects.get(qr_code=codigo_qr, is_active=True)
        except Event.DoesNotExist:
            return Response({'error': 'QR inválido o evento no activo.'}, status=404)

        p = self.get_participante()

        # Crear inscripción si no existe (auto-inscripción al escanear)
        Enrollment.objects.get_or_create(participant=p, event=sesion)

        # Registrar asistencia (idempotente — el unique constraint
        # event+participant evita duplicados)
        ip = (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR')
        )
        registro, created = Attendance.objects.get_or_create(
            participant=p,
            event=sesion,
            defaults={'ip_address': ip},
        )

        return Response({
            'ok': True,
            'created': created,
            'already_registered': not created,
            'sesion_id': sesion.id,
            'sesion_titulo': sesion.title or sesion.day_of_week,
            'fecha': sesion.date.strftime('%Y-%m-%d'),
            'hora': sesion.start_time.strftime('%H:%M'),
        })


class DashboardView(_AuthenticatedBase):
    """GET /api/v1/public/account/dashboard/ → stats + próximos eventos + recientes."""

    def get(self, request):
        p = self.get_participante()
        today = timezone.localdate()

        certificados = Certificate.objects.filter(
            Q(national_id=p.national_id) if p.national_id else Q(email__iexact=p.email)
        ).order_by('-course_date')
        total_horas = sum(c.hours or 0 for c in certificados)

        confirmados_ids = set(Enrollment.objects.filter(participant=p).values_list('event_id', flat=True))
        asistidos_ids   = set(Attendance.objects.filter(participant=p).values_list('event_id', flat=True))

        proximos = (Event.objects
            .filter(is_active=True, id__in=confirmados_ids, date__gte=today)
            .order_by('date', 'start_time')[:3])

        recomendados = (Event.objects
            .filter(is_active=True, date__gte=today)
            .exclude(id__in=confirmados_ids)
            .order_by('date', 'start_time')[:5])

        return Response({
            'participante':   ParticipanteSerializer(p).data,
            'stats': {
                'certificados':       certificados.count(),
                'total_horas':        total_horas,
                'eventos_inscrito':   len(confirmados_ids),
                'eventos_asistido':   len(asistidos_ids),
            },
            'proximos':       SesionMobileSerializer(proximos, many=True).data,
            'recomendados':   SesionMobileSerializer(recomendados, many=True).data,
            'certificados_recientes': CertificadoSerializer(certificados[:3], many=True).data,
        })
