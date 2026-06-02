from django.db import models
from django.db.models import Count
from django.utils import timezone


class EventQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def upcoming(self):
        return self.filter(is_active=True, date__gte=timezone.now().date())

    def past(self):
        return self.filter(date__lt=timezone.now().date())

    def with_stats(self):
        return self.annotate(
            enrolled_total=Count('enrollments', distinct=True),
            attendees_total=Count('attendances', distinct=True),
        )


class EventManager(models.Manager):
    def get_queryset(self):
        return EventQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def upcoming(self):
        return self.get_queryset().upcoming()

    def past(self):
        return self.get_queryset().past()

    def with_stats(self):
        return self.get_queryset().with_stats()
