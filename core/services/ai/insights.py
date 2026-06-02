"""Fase 10: Insights narrativos del dashboard — PLACEHOLDER."""
from .client import is_configured


def get_dashboard_metrics() -> dict:
    """Recolecta métricas brutas (sin IA — esto ya podemos calcularlo)."""
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models import Count
    from core.models import Certificate, Event, Enrollment, Attendance

    now = timezone.now()
    last_30 = now - timedelta(days=30)
    prev_30 = now - timedelta(days=60)

    certs_this = Certificate.objects.filter(created_at__gte=last_30).count()
    certs_prev = Certificate.objects.filter(created_at__gte=prev_30, created_at__lt=last_30).count()
    sesiones_mes = Event.objects.filter(date__gte=last_30.date()).count()

    return {
        'mes_actual': {
            'certificados_emitidos': certs_this,
            'cambio_vs_anterior_pct': round(
                (certs_this - certs_prev) / max(certs_prev, 1) * 100, 1
            ),
        },
        'sesiones_mes': sesiones_mes,
    }


def generate_insights() -> dict:
    metrics = get_dashboard_metrics()
    if not is_configured():
        return {
            'implemented': False,
            'message': 'Narrativa IA pendiente (Fase 10). Configura ANTHROPIC_API_KEY.',
            'metrics': metrics,
        }
    # TODO Fase 10
    return {'implemented': False, 'insights': [], 'metrics': metrics}
