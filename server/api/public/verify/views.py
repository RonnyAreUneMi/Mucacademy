from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Certificate


class VerifyCertificateView(APIView):
    """GET /<hash>/ → datos completos de un certificado para la página de verificación."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, hash):
        cert = (
            Certificate.objects
            .filter(verification_hash=hash)
            .select_related('batch')
            .first()
        )
        if not cert:
            return Response({'found': False, 'hash': hash}, status=404)

        Certificate.objects.filter(pk=cert.pk).update(search_count=cert.search_count + 1)

        batch = cert.batch
        return Response({
            'found': True,
            'hash': cert.verification_hash,
            'certificate': {
                'first_name': cert.first_name,
                'last_name': cert.last_name,
                'national_id': cert.national_id,
                'email': cert.email,
                'course': cert.course,
                'course_date': cert.course_date.isoformat() if cert.course_date else None,
                'issued_at': cert.created_at.isoformat() if cert.created_at else None,
                'hours': cert.hours,
                'download_count': cert.download_count,
                'search_count': cert.search_count + 1,
            },
            'batch': {
                'name': batch.name if batch else None,
                'faculty_code': batch.faculty if batch else None,
                'faculty_display': batch.get_faculty_display() if batch else None,
                'template': batch.template if batch else None,
            } if batch else None,
        })
