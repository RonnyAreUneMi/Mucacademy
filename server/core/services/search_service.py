from django.db.models import Q
from core.models import Certificate, CertificateBatch

def search_certificates(query):
    """
    Search certificates by various fields.
    Optimized with select_related.
    """
    if not query:
        return []

    query = query.strip()

    # Validation constraint: Minimum 3 chars to search?
    if len(query) < 3:
        return []

    return Certificate.objects.filter(
        Q(national_id__icontains=query) |
        Q(email__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query)
    ).select_related('batch').order_by('-created_at')

def get_certificate_by_hash(verification_hash):
    return Certificate.objects.filter(verification_hash=verification_hash).first()
