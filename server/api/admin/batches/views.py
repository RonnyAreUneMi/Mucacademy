import random
import uuid
from datetime import date

from django.http import FileResponse, HttpResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from api.admin.permissions import IsPanelAdmin
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import Certificate, CertificateBatch
from core.services.excel_service import analyze_excel_headers, procesar_archivo_excel_lote_business
from core.services.pdf_service import generate_certificate_pdf
from api.common.viewsets import AuditedModelViewSet

from .serializers import LoteListSerializer, LoteDetailSerializer, LoteWriteSerializer


class LoteViewSet(AuditedModelViewSet):
    """CRUD de lotes de certificados."""
    queryset = CertificateBatch.objects.all().select_related('administrator')
    permission_classes = [IsPanelAdmin]
    filterset_fields = ['is_active', 'faculty', 'template', 'customize_design']
    search_fields = ['name']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    audit_verbose_name = 'lote'

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return LoteWriteSerializer
        if self.action == 'retrieve':
            return LoteDetailSerializer
        return LoteListSerializer

    def audit_detail(self, instance, action):
        return f'Lote #{instance.pk} ({instance.name})'

    def perform_create(self, serializer):
        instance = serializer.save(administrator=self.request.user)
        self.log_audit(self._action_code('create'), self.audit_detail(instance, 'create'))

    # ── Custom actions ──────────────────────────────────────────

    @action(detail=True, methods=['get'])
    def analyze_excel(self, request, pk=None):
        """Devuelve columnas detectadas + sugerencias de mapeo."""
        result = analyze_excel_headers(pk)
        if not result.get('success'):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=True, methods=['post'])
    def process_excel(self, request, pk=None):
        """Procesa el Excel con un mapping opcional."""
        mapping = request.data.get('mapping')
        ok, msg = procesar_archivo_excel_lote_business(pk, mapping=mapping)
        if not ok:
            return Response({'success': False, 'error': msg}, status=status.HTTP_400_BAD_REQUEST)
        lote = self.get_object()
        self.log_audit('PROCESAR_EXCEL', f'Lote #{lote.pk} procesado: {msg}')
        return Response({'success': True, 'message': msg})

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        lote = self.get_object()
        lote.is_active = not lote.is_active
        lote.save(update_fields=['is_active'])
        self.log_audit('TOGGLE_LOTE', f'Lote #{lote.pk} → is_active={lote.is_active}')
        return Response({'id': lote.id, 'activo': lote.is_active})

    @action(detail=True, methods=['get'], url_path='preview-pdf')
    @method_decorator(xframe_options_exempt)
    def preview_pdf(self, request, pk=None):
        """GET → devuelve un PDF de preview con datos dummy para este lote."""
        lote = self.get_object()
        dummy_cert = Certificate(
            batch=lote,
            national_id='0999999999',
            first_name='ESTUDIANTE',
            last_name='DE PRUEBA',
            email='prueba@unemi.edu.ec',
            course='CURSO DE DEMOSTRACIÓN',
            course_date=date.today(),
            hours=40,
            verification_hash=uuid.uuid4(),
        )
        dummy_cert.id = random.randint(10000, 99999)
        try:
            pdf_buffer = generate_certificate_pdf(dummy_cert)
            response = FileResponse(pdf_buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="Preview_{lote.id}.pdf"'
            return response
        except Exception as e:
            return HttpResponse(f'Error generando preview: {e}', status=500)
