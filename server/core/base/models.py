"""Abstract base models reused across all domains."""
from django.db import models


class TimestampedModel(models.Model):
    """Abstract mixin that adds `created_at` and `updated_at` timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SingletonModel(models.Model):
    """Base for models that must have a single row (e.g. global settings)."""

    class Meta:
        abstract = True

    @classmethod
    def load(cls):
        """Return the singleton instance, creating it on first access."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
