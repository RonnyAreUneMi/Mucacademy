from django.db import models
from django.db.models import Count


class BatchQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def with_stats(self):
        return self.annotate(
            certificates_total=Count('certificates', distinct=True),
        )

    def by_faculty(self, code: str):
        return self.filter(faculty=code)


class BatchManager(models.Manager):
    def get_queryset(self):
        return BatchQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def with_stats(self):
        return self.get_queryset().with_stats()
