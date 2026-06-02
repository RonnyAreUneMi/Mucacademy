from datetime import timedelta

from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import (
    Certificate, CertificateBatch, AuditLog,
    Event, Participant, Enrollment, AccessRequest,
)


class AdminDashboardView(APIView):
    """GET /api/v1/admin/dashboard/ → todas las métricas del dashboard admin."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        now = timezone.now()
        today = now.date()

        total_certificados = Certificate.objects.count()
        total_descargas = Certificate.objects.aggregate(total=Sum('download_count'))['total'] or 0
        total_busquedas = Certificate.objects.aggregate(total=Sum('search_count'))['total'] or 0
        total_lotes = CertificateBatch.objects.count()
        total_participantes = Participant.objects.count()
        total_eventos = Event.objects.filter(is_active=True).count()
        total_inscripciones = Enrollment.objects.filter(confirmed=True).count()
        solicitudes_pendientes = AccessRequest.objects.filter(status='pending').count()

        # Lotes recientes
        recent_lotes = list(
            CertificateBatch.objects.order_by('-created_at')
            .values('id', 'name', 'faculty', 'created_at')[:5]
        )

        # Auditoría reciente
        auditoria = list(
            AuditLog.objects.select_related('user')[:10]
            .values('id', 'action', 'details', 'created_at',
                    'user__username', 'user__first_name', 'user__last_name')
        )

        # Distribución por facultad
        stats_facultad = list(
            Certificate.objects.values('batch__faculty')
            .annotate(total=Count('id')).order_by('-total')
        )
        labels_facultad = [i['batch__faculty'] for i in stats_facultad if i['batch__faculty']]
        data_facultad = [i['total'] for i in stats_facultad if i['batch__faculty']]

        # Top 5 lotes por descargas
        top_lotes = list(
            Certificate.objects.values('batch__name')
            .annotate(downloads=Sum('download_count'))
            .order_by('-downloads')[:5]
        )
        labels_top_lotes = [i['batch__name'] for i in top_lotes]
        data_top_lotes = [i['downloads'] or 0 for i in top_lotes]

        # Próximos eventos (próximos 7 días)
        upcoming_sessions_qs = (
            Event.objects
            .filter(is_active=True, date__gte=today, date__lte=today + timedelta(days=7))
            .annotate(num_inscritos=Count('enrollments'))
            .order_by('date', 'start_time')[:5]
        )
        upcoming_sessions = [
            {
                'id': s.id,
                'titulo': s.title or s.day_of_week,
                'fecha': s.date.isoformat(),
                'fecha_display': s.date.strftime('%d/%m'),
                'dia_semana': s.day_of_week,
                'hora_inicio': s.start_time.strftime('%H:%M'),
                'hora_fin': s.end_time.strftime('%H:%M'),
                'modalidad': s.modality,
                'lugar': s.location,
                'inscritos': s.num_inscritos,
                'capacidad': s.capacity,
                'es_hoy': s.date == today,
            }
            for s in upcoming_sessions_qs
        ]

        # ── Series diarias últimos 14 días para sparklines/charts ──
        last_14_days = today - timedelta(days=14)

        def _serie_diaria_count(qs, date_field: str):
            """Devuelve [count_dia_-13, ..., count_hoy] como lista de 14 items."""
            counts_by_date = dict(
                qs.filter(**{f'{date_field}__date__gte': last_14_days})
                .annotate(d=TruncDate(date_field))
                .values('d').annotate(c=Count('id')).values_list('d', 'c')
            )
            out = []
            for offset in range(13, -1, -1):
                d = today - timedelta(days=offset)
                out.append(counts_by_date.get(d, 0))
            return out

        labels_daily = [
            (today - timedelta(days=offset)).strftime('%d/%m')
            for offset in range(13, -1, -1)
        ]
        data_daily = _serie_diaria_count(Certificate.objects.all(), 'created_at')
        data_inscripciones_daily = _serie_diaria_count(
            Enrollment.objects.filter(confirmed=True), 'enrolled_at'
        )
        data_eventos_daily = _serie_diaria_count(
            Event.objects.filter(is_active=True), 'created_at'
        )

        return Response({
            'totals': {
                'certificados': total_certificados,
                'descargas': total_descargas,
                'busquedas': total_busquedas,
                'lotes': total_lotes,
                'participantes': total_participantes,
                'eventos_activos': total_eventos,
                'inscripciones': total_inscripciones,
                'solicitudes_pendientes': solicitudes_pendientes,
            },
            'upcoming_sessions': upcoming_sessions,
            'recent_lotes': recent_lotes,
            'auditoria': [
                {
                    'id': a['id'],
                    'accion': a['action'],
                    'detalle': a['details'],
                    'fecha': a['created_at'].isoformat(),
                    'usuario_username': a['user__username'],
                    'usuario_nombre': f"{a['user__first_name']} {a['user__last_name']}".strip(),
                }
                for a in auditoria
            ],
            'charts': {
                'facultad': {'labels': labels_facultad, 'data': data_facultad},
                'top_lotes': {'labels': labels_top_lotes, 'data': data_top_lotes},
                'daily': {'labels': labels_daily, 'data': data_daily},
                'daily_inscripciones': data_inscripciones_daily,
                'daily_eventos': data_eventos_daily,
            },
        })
