from django.db import models
from django.db.models import Q


class ParticipantQuerySet(models.QuerySet):
    def search(self, query: str):
        query = (query or '').strip()
        if not query:
            return self.none()
        tokens = query.split()
        q = Q(national_id__icontains=query) | Q(email__icontains=query)
        for t in tokens:
            q |= Q(first_name__icontains=t) | Q(last_name__icontains=t)
        return self.filter(q).distinct()

    def leaders(self):
        return self.filter(is_leader=True)

    def with_counts(self):
        return self.annotate(certificates_total=models.Count('certificates', distinct=True))


class ParticipantManager(models.Manager):
    def get_queryset(self):
        return ParticipantQuerySet(self.model, using=self._db)

    def search(self, q):
        return self.get_queryset().search(q)

    def leaders(self):
        return self.get_queryset().leaders()
