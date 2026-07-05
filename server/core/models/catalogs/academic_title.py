"""AcademicTitle — admin-editable catalog of academic titles.

A dynamic lookup table of the academic titles a speaker (ponente) can hold:
Dr., Mg., Ing., Lic., PhD, MSc, etc. Seeded on first migration with the most
common ones. The speaker form picks from this catalog instead of free-typing
the title, so it stays consistent across events.
"""
from django.db import models


class AcademicTitle(models.Model):
    """Academic title / honorific used for speakers (e.g. "Dr.", "Ing.")."""
    abbreviation = models.CharField(
        max_length=20, unique=True,
        help_text='Short form stored on the speaker (e.g. "Dr.", "Ing.").',
    )
    name = models.CharField(
        max_length=80,
        help_text='Full name of the title (e.g. "Doctor", "Ingeniero").',
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        help_text='Display order in select widgets (lower first).',
    )
    is_active = models.BooleanField(
        default=True, db_index=True,
        help_text='If False, hidden from new selects but keeps existing values intact.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Academic title'
        verbose_name_plural = 'Academic titles'
        ordering = ['sort_order', 'abbreviation']

    def __str__(self):
        return self.abbreviation
