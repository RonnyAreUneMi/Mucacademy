import io
import zipfile

from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import Certificate, Participant
from core.services.pdf_service import generate_certificate_pdf

from .serializers import CertificadoListSerializer


class PublicCertificadoViewSet(viewsets.ReadOnlyModelViewSet):
    """Acceso público a certificados: búsqueda, verificación y descarga por hash."""
    queryset = Certificate.objects.with_relations()
    serializer_class = CertificadoListSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'verification_hash'

    def list(self, request, *args, **kwargs):
        q = request.query_params.get('q', '').strip()
        if len(q) < 3:
            return Response({'count': 0, 'results': []})
        # Search con AND entre tokens + dedupe por (national_id, course)
        ids = list(self.get_queryset().search(q).deduped_by_person_course().values_list('id', flat=True)[:50])
        qs = self.get_queryset().filter(id__in=ids)
        return Response({
            'count': len(ids),
            'results': self.get_serializer(qs, many=True).data,
        })

    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'results': []})

        tokens = [t for t in query.split() if t]
        if not tokens:
            return Response({'results': []})

        q = Q()
        for t in tokens:
            q &= (Q(national_id__icontains=t) | Q(email__icontains=t) |
                  Q(first_name__icontains=t) | Q(last_name__icontains=t))

        seen, results = set(), []
        for p in Participant.objects.filter(q)[:20]:
            name = f'{p.first_name.strip()} {p.last_name.strip()}'.strip()
            key = name.lower()
            if name and key not in seen:
                seen.add(key)
                results.append({'name': name})
                if len(results) >= 12:
                    break

        if len(results) < 12:
            cert_q = Q()
            for t in tokens:
                cert_q &= (Q(national_id__icontains=t) | Q(email__icontains=t) |
                           Q(first_name__icontains=t) | Q(last_name__icontains=t))
            orphans = (
                Certificate.objects.filter(cert_q, participant__isnull=True)
                .values('first_name', 'last_name').distinct()[:20]
            )
            for o in orphans:
                name = f'{(o["first_name"] or "").strip()} {(o["last_name"] or "").strip()}'.strip()
                key = name.lower()
                if name and key not in seen:
                    seen.add(key)
                    results.append({'name': name})
                    if len(results) >= 12:
                        break

        return Response({'results': results})

    @action(detail=True, methods=['get'])
    def verify(self, request, verification_hash=None):
        try:
            cert = self.get_queryset().get(verification_hash=verification_hash)
        except Certificate.DoesNotExist:
            return Response({'valid': False, 'message': 'Certificado no encontrado'},
                            status=status.HTTP_404_NOT_FOUND)

        Certificate.objects.filter(pk=cert.pk).update(search_count=cert.search_count + 1)

        return Response({
            'valid': True,
            'nombres': cert.first_name,
            'apellidos': cert.last_name,
            'cedula': cert.national_id,
            'curso': cert.course,
            'fecha_curso': cert.course_date,
            'horas': cert.hours,
            'lote': cert.batch.name if cert.batch else None,
            'hash': cert.verification_hash,
        })

    @action(detail=False, methods=['get'], url_path='bulk-download')
    def bulk_download(self, request):
        """Descarga en ZIP todos los certificados que coincidan con ?q=X."""
        query = request.query_params.get('q', '').strip()
        if not query:
            return HttpResponse('No query provided', status=status.HTTP_400_BAD_REQUEST)

        qs = self.get_queryset().search(query)
        if not qs.exists():
            return HttpResponse('No certificates found', status=status.HTTP_404_NOT_FOUND)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            seen_names = {}
            for cert in qs:
                try:
                    pdf_buffer = generate_certificate_pdf(cert)
                    safe_curso = slugify(cert.course) or 'certificado'
                    base = f'{safe_curso}_{cert.national_id}'
                    count = seen_names.get(base, 0)
                    seen_names[base] = count + 1
                    filename = f'{base}.pdf' if count == 0 else f'{base}_{count + 1}.pdf'
                    zf.writestr(filename, pdf_buffer.getvalue())
                except Exception:
                    continue

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.read(), content_type='application/zip')
        zip_name = f'certificados_{slugify(query)}.zip'
        response['Content-Disposition'] = f'attachment; filename="{zip_name}"'
        response['Cache-Control'] = 'no-store'
        return response

    @action(detail=True, methods=['get'])
    def download(self, request, verification_hash=None):
        try:
            cert = self.get_queryset().get(verification_hash=verification_hash)
        except Certificate.DoesNotExist:
            raise Http404('Certificado no encontrado')

        buffer = generate_certificate_pdf(cert)

        # Vista previa: se sirve inline (visible en el navegador) y NO cuenta como descarga.
        inline = request.query_params.get('inline') in ('1', 'true')
        if not inline:
            Certificate.objects.filter(pk=cert.pk).update(
                download_count=cert.download_count + 1,
                last_download_at=timezone.now(),
            )

        filename = f'Certificado_{cert.national_id}_{cert.verification_hash[:8]}.pdf'
        response = FileResponse(buffer, as_attachment=not inline, filename=filename, content_type='application/pdf')
        response['Cache-Control'] = 'no-store'
        return response
