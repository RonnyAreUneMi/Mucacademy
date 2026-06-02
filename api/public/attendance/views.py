from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import (
    Participant, Certificate, Event, Enrollment,
)

from .serializers import (
    AttendanceConfirmInputSerializer, UpdatePhoneInputSerializer,
)


def _participant_data(p):
    return {
        'id': p.id,
        'cedula': p.national_id,
        'nombres': p.first_name,
        'apellidos': p.last_name,
        'email': p.email,
        'celular': p.phone or '',
        'cursos': list(p.certificates.values_list('course', flat=True).distinct()),
        'cursos_count': p.certificates.count(),
    }


class AttendanceSearchView(APIView):
    """GET ?q=X → lista participantes para confirmar asistencia."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 3:
            return Response({'results': []})

        tokens = query.split()
        q_filter = Q(national_id__icontains=query) | Q(email__icontains=query)
        for t in tokens:
            q_filter |= Q(first_name__icontains=t) | Q(last_name__icontains=t)

        participantes = Participant.objects.filter(q_filter)[:20]
        return Response({'results': [_participant_data(p) for p in participantes]})


class AttendanceVerifyView(APIView):
    """GET ?q=X → búsqueda enriquecida con eventos disponibles y estado de confirmación."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({
                'personas': [], 'total': 0,
                'dias_disponibles': self._sessions_by_day(),
                'confirmacion_existente': None,
            })

        tokens = query.split()
        q_filter = Q(national_id__icontains=query) | Q(email__icontains=query)
        for t in tokens:
            q_filter |= Q(first_name__icontains=t) | Q(last_name__icontains=t)

        participantes = list(Participant.objects.filter(q_filter)[:50])
        personas = []
        for p in participantes:
            personas.append({
                **_participant_data(p),
                'participante_id': p.id,
                'cert_id': p.certificates.values_list('id', flat=True).first(),
            })

        conf_existente = None
        if len(personas) == 1:
            p = participantes[0]
            conf = (
                Enrollment.objects
                .filter(participant=p, confirmed=True)
                .select_related('event').first()
            )
            if conf:
                conf_existente = {
                    'dia': conf.event.day_of_week,
                    'fecha': conf.event.date.strftime('%d/%m/%Y'),
                    'horario': conf.event.label,
                }

        return Response({
            'personas': personas,
            'total': len(personas),
            'persona': personas[0] if len(personas) == 1 else None,
            'dias_disponibles': self._sessions_by_day(),
            'confirmacion_existente': conf_existente,
        })

    @staticmethod
    def _sessions_by_day():
        sesiones = Event.objects.filter(is_active=True).order_by('date', 'start_time')
        dias = {}
        for s in sesiones:
            key = f"{s.day_of_week} - {s.date.strftime('%d/%m/%Y')}"
            dias.setdefault(key, []).append({
                'id': s.id,
                'label': s.label,
                'titulo': s.title,
                'cupos': s.available_seats if s.available_seats is not None else 9999,
                'llena': s.is_full,
            })
        return dias


class AttendanceSessionsView(APIView):
    """GET → eventos activos agrupados por día (para select dependiente)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({'dias': AttendanceVerifyView._sessions_by_day()})


class AttendanceConfirmView(APIView):
    """POST → crea Enrollment para un participante + evento."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = AttendanceConfirmInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            sesion = Event.objects.get(id=data['sesion_id'], is_active=True)
        except Event.DoesNotExist:
            return Response({'ok': False, 'error': 'Evento no encontrado.'},
                            status=status.HTTP_404_NOT_FOUND)

        participante = None
        if data.get('participante_id'):
            try:
                participante = Participant.objects.get(id=data['participante_id'])
            except Participant.DoesNotExist:
                return Response({'ok': False, 'error': 'Participante no encontrado.'},
                                status=status.HTTP_404_NOT_FOUND)
        elif data.get('cert_id'):
            try:
                cert = Certificate.objects.get(id=data['cert_id'])
                participante = cert.participant
                if not participante:
                    return Response({'ok': False, 'error': 'Participante no vinculado.'},
                                    status=status.HTTP_404_NOT_FOUND)
            except Certificate.DoesNotExist:
                return Response({'ok': False, 'error': 'Certificado no encontrado.'},
                                status=status.HTTP_404_NOT_FOUND)

        if sesion.is_full:
            return Response({
                'ok': False,
                'error': f'Este evento ya alcanzó el cupo máximo de {sesion.capacity} personas.',
            }, status=status.HTTP_409_CONFLICT)

        conf, created = Enrollment.objects.get_or_create(
            participant=participante, event=sesion, defaults={'confirmed': True},
        )

        if not created:
            return Response({'ok': True, 'already': True,
                             'message': 'Ya estás confirmado para este evento.'})

        cupos = sesion.available_seats
        cupos_msg = f'Quedan {cupos} cupos.' if cupos is not None else ''
        return Response({
            'ok': True, 'already': False,
            'message': f'Asistencia confirmada para {sesion.day_of_week} {sesion.label}. {cupos_msg} ¡Recuerda asistir!',
        })


class AttendanceUpdatePhoneView(APIView):
    """POST → actualiza celular del participante (y sincroniza certificados)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = UpdatePhoneInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        celular = (ser.validated_data.get('celular') or '').strip()

        pid = ser.validated_data.get('participante_id')
        cid = ser.validated_data.get('cert_id')

        if pid:
            try:
                p = Participant.objects.get(id=pid)
                p.phone = celular
                p.save(update_fields=['phone'])
                Certificate.objects.filter(participant=p).update(phone=celular)
                return Response({'ok': True, 'celular': celular})
            except Participant.DoesNotExist:
                return Response({'ok': False, 'error': 'Participante no encontrado.'},
                                status=status.HTTP_404_NOT_FOUND)

        if cid:
            try:
                cert = Certificate.objects.get(id=cid)
                Certificate.objects.filter(national_id=cert.national_id).update(phone=celular)
                if cert.participant:
                    cert.participant.phone = celular
                    cert.participant.save(update_fields=['phone'])
                return Response({'ok': True, 'celular': celular})
            except Certificate.DoesNotExist:
                return Response({'ok': False, 'error': 'Certificado no encontrado.'},
                                status=status.HTTP_404_NOT_FOUND)

        return Response({'ok': False, 'error': 'Faltan datos.'},
                        status=status.HTTP_400_BAD_REQUEST)
