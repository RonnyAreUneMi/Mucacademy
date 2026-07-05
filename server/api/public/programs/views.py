"""API pública de programas: lista y detalle (solo programas publicados)."""
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Program
from .serializers import PublicProgramListSerializer, PublicProgramDetailSerializer


class PublicProgramListView(APIView):
    """GET /api/v1/public/programs/ → programas publicados (is_open)."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = Program.objects.filter(is_active=True, is_open=True).order_by('name')
        data = PublicProgramListSerializer(qs, many=True, context={'request': request}).data
        return Response({'count': len(data), 'results': data})


class PublicProgramDetailView(APIView):
    """GET /api/v1/public/programs/<id>/ → detalle con seminarios + nota mínima."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request, program_id):
        program = Program.objects.filter(pk=program_id, is_active=True, is_open=True).first()
        if program is None:
            return Response({'error': 'Programa no encontrado.'}, status=404)
        return Response(
            PublicProgramDetailSerializer(program, context={'request': request}).data
        )
