from django.db import models
from django.db.models import Q


class CertificateQuerySet(models.QuerySet):
    def search(self, query: str):
        """Search certificates.

        Rules:
        - Exact match of national_id / email / verification_hash → those rows.
        - Otherwise split into tokens; EACH token must appear in name fields
          (AND across tokens, OR within each field).
        """
        query = (query or '').strip()
        if not query:
            return self.none()

        exact_filter = (
            Q(national_id__iexact=query)
            | Q(email__iexact=query.lower())
            | Q(verification_hash__iexact=query)
        )

        tokens = [t for t in query.split() if t]
        name_filter = Q()
        for t in tokens:
            name_filter &= (
                Q(first_name__icontains=t)
                | Q(last_name__icontains=t)
                | Q(national_id__icontains=t)
                | Q(email__icontains=t)
            )

        combined = exact_filter | name_filter if tokens else exact_filter
        return self.filter(combined).distinct()

    def with_relations(self):
        return self.select_related('batch', 'participant')

    def downloaded(self):
        return self.filter(download_count__gt=0)

    def by_faculty(self, faculty_code: str):
        return self.filter(batch__faculty=faculty_code)

    def deduped_by_person_course(self):
        """Dedupe by (national_id, course) → keep the most recent of each pair."""
        from django.db.models import Max
        latest_ids = (
            self.values('national_id', 'course')
            .annotate(latest_id=Max('id'))
            .values_list('latest_id', flat=True)
        )
        return self.filter(id__in=list(latest_ids))


class CertificateManager(models.Manager):
    def get_queryset(self):
        return CertificateQuerySet(self.model, using=self._db)

    def search(self, q):
        return self.get_queryset().search(q)

    def downloaded(self):
        return self.get_queryset().downloaded()

    def with_relations(self):
        return self.get_queryset().with_relations()

    def deduped_by_person_course(self):
        return self.get_queryset().deduped_by_person_course()
