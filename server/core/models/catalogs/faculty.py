"""Faculty — admin-editable dynamic lookup table.

Seeded on first migration with the five UNEMI faculties. Admins can add,
edit, deactivate, or reorder rows from the admin panel without redeploys.
"""
from django.db import models


class Faculty(models.Model):
    """Academic faculty or program of UNEMI."""
    code = models.CharField(
        max_length=20, unique=True,
        help_text='Short unique code (e.g. FACI, FACS). Used as FK from other models.',
    )
    name = models.CharField(
        max_length=120,
        help_text='Full faculty name (e.g. "FACI - Engineering").',
    )
    description = models.TextField(
        blank=True, default='',
        help_text='Optional faculty description.',
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        help_text='Display order in select widgets (lower first).',
    )
    is_active = models.BooleanField(
        default=True, db_index=True,
        help_text='If False, hidden from new selects but keeps existing FKs intact.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Faculty'
        verbose_name_plural = 'Faculties'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name
