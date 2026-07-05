from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Certificate, CertificateBatch, Participant, Event


class PublicStatsView(APIView):
    """Conteos agregados para la landing pública."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            'total_certificados': Certificate.objects.count(),
            'total_seminarios': CertificateBatch.objects.count(),
            'total_participantes': Participant.objects.count(),
            'total_sesiones_activas': Event.objects.filter(is_active=True).count(),
        })
