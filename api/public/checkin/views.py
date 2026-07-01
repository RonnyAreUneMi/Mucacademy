from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import (
    Event, Participant, Certificate,
    Enrollment, Attendance,
)


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class CheckinSessionView(APIView):
    """GET → devuelve info básica del evento identificado por su código QR."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, codigo_qr):
        sesion = get_object_or_404(Event, qr_code=codigo_qr, is_active=True)
        return Response({
            'id': sesion.id,
            'codigo_qr': sesion.qr_code,
            'titulo': sesion.title or sesion.day_of_week,
            'descripcion': sesion.description,
            'dia_semana': sesion.day_of_week,
            'fecha': sesion.date.strftime('%Y-%m-%d'),
            'hora_inicio': sesion.start_time.strftime('%H:%M'),
            'hora_fin': sesion.end_time.strftime('%H:%M'),
            'lugar': sesion.location,
            'modalidad': sesion.modality,
        })


class CheckinSearchView(APIView):
    """GET ?q=X → busca participantes en el contexto del QR."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, codigo_qr):
        sesion = get_object_or_404(Event, qr_code=codigo_qr, is_active=True)
        query = request.query_params.get('q', '').strip()
        if len(query) < 3:
            return Response({'results': []})

        tokens = query.split()
        q_filter = Q(national_id__icontains=query) | Q(email__icontains=query)
        for t in tokens:
            q_filter |= Q(first_name__icontains=t) | Q(last_name__icontains=t)

        participantes = Participant.objects.filter(q_filter)[:15]
        results = []
        for p in participantes:
            results.append({
                'id': p.id,
                'cedula': p.national_id,
                'nombres': p.first_name,
                'apellidos': p.last_name,
                'email': p.email,
                'already_registered': Attendance.objects.filter(
                    event=sesion, participant=p
                ).exists(),
                'is_confirmed': Enrollment.objects.filter(
                    event=sesion, participant=p, confirmed=True
                ).exists(),
            })
        return Response({'results': results})


class CheckinRegisterView(APIView):
    """POST → registra asistencia (marca presente) si hay confirmación previa."""
    permission_classes = [permissions.AllowAny]

    def post(self, request, codigo_qr):
        sesion = get_object_or_404(Event, qr_code=codigo_qr, is_active=True)

        pid = request.data.get('id') or request.data.get('cert_id')
        if not pid:
            return Response({'ok': False, 'error': 'Datos incompletos.'},
                            status=status.HTTP_400_BAD_REQUEST)

        participante = None
        try:
            participante = Participant.objects.get(id=pid)
        except Participant.DoesNotExist:
            try:
                cert = Certificate.objects.get(id=pid)
                participante = cert.participant
            except Certificate.DoesNotExist:
                pass

        if not participante:
            return Response({'ok': False, 'error': 'Participante no encontrado.'},
                            status=status.HTTP_404_NOT_FOUND)

        # Bloqueo por inasistencias previas
        blocked = Enrollment.objects.filter(
            participant=participante, blocked=True
        ).exists()
        if blocked:
            return Response({
                'ok': False,
                'error': 'Tu cuenta está bloqueada por inasistencias previas. Contacta al administrador.',
            }, status=status.HTTP_403_FORBIDDEN)

        # Confirmación previa requerida
        is_confirmed = Enrollment.objects.filter(
            participant=participante, event=sesion, confirmed=True
        ).exists()
        if not is_confirmed:
            return Response({
                'ok': False,
                'error': f'No tienes una confirmación de cupo registrada para el evento de {sesion.day_of_week} {sesion.label}.',
            }, status=status.HTTP_403_FORBIDDEN)

        registro, created = Attendance.objects.get_or_create(
            event=sesion, participant=participante,
            defaults={'ip_address': _get_client_ip(request)},
        )

        if not created:
            return Response({
                'ok': True, 'already': True,
                'message': '¡Ya registraste tu asistencia anteriormente!',
                'nombre': f'{participante.first_name} {participante.last_name}',
            })

        # Si el seminario pertenece a un programa, tras esta asistencia el
        # participante podría haber completado todos los seminarios → intentar
        # emitir el certificado de programa (requiere además aprobar la eval).
        if sesion.program_id:
            try:
                from core.services import programs as program_service
                program_service.check_and_issue(sesion.program, participante)
            except Exception:
                pass  # nunca bloquear el check-in por esto

        return Response({
            'ok': True, 'already': False,
            'message': '¡Gracias por estar aquí! Tu asistencia fue registrada exitosamente.',
            'nombre': f'{participante.first_name} {participante.last_name}',
            'hora': timezone.now().strftime('%H:%M'),
        })
