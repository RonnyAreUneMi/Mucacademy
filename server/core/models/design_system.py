"""Admin panel Design System tokens — singleton.

A single row holds the design tokens (colors, fonts, radii, shadows, etc.)
consumed by the panel `:root` CSS via context processor. Changing a value
here updates the whole UI.
"""
from django.db import models

from core.base.models import SingletonModel, TimestampedModel


class UIDesignTokens(SingletonModel, TimestampedModel):
    """Admin panel design-system tokens.

    Source of truth for the CSS custom properties declared in `:root`
    inside `panel/base.html`.
    """

    # ─── Branding / colores principales ──────────────────────
    color_brand = models.CharField(
        max_length=9,
        default='#F58830',
        help_text='Color de marca principal (acento UNEMI / CertifAI)',
    )
    color_brand_dark = models.CharField(
        max_length=9,
        default='#D97520',
        help_text='Variante oscura del color de marca (gradientes/hover)',
    )
    color_accent = models.CharField(
        max_length=9,
        default='#162054',
        help_text='Acento secundario · UNEMI azul institucional',
    )

    # ─── Colores de superficie ────────────────────────────────
    color_bg_dark = models.CharField(max_length=9, default='#0A1535', help_text='Fondo principal modo oscuro')
    color_bg_light = models.CharField(max_length=9, default='#F8FAFC', help_text='Fondo principal modo claro')
    color_card_dark = models.CharField(max_length=9, default='#152448', help_text='Fondo de cards modo oscuro')
    color_card_light = models.CharField(max_length=9, default='#FFFFFF', help_text='Fondo de cards modo claro')

    # ─── Texto ────────────────────────────────────────────────
    color_text_dark = models.CharField(max_length=9, default='#E2E8F0', help_text='Texto principal modo oscuro')
    color_text_light = models.CharField(max_length=9, default='#0F172A', help_text='Texto principal modo claro')
    color_text_muted_dark = models.CharField(max_length=9, default='#94A3B8', help_text='Texto secundario modo oscuro')
    color_text_muted_light = models.CharField(max_length=9, default='#64748B', help_text='Texto secundario modo claro')

    # ─── Estado (semánticos) ──────────────────────────────────
    # Estado · sólo paleta UNEMI (naranja/azul) + rojo para errores críticos
    color_success = models.CharField(max_length=9, default='#1E40AF', help_text='Estado positivo · azul')
    color_danger  = models.CharField(max_length=9, default='#DC2626', help_text='Errores críticos · rojo')
    color_warning = models.CharField(max_length=9, default='#F58830', help_text='Aviso · naranja brand')
    color_info    = models.CharField(max_length=9, default='#3B82F6', help_text='Información · azul claro')

    # ─── Tipografía ───────────────────────────────────────────
    font_sans = models.CharField(
        max_length=255,
        default="'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
        help_text='Stack de fuente para UI general',
    )
    font_display = models.CharField(
        max_length=255,
        default="'Sora', 'Inter', system-ui, sans-serif",
        help_text='Stack de fuente para títulos/branding',
    )
    font_mono = models.CharField(
        max_length=255,
        default="'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace",
        help_text='Stack de fuente monoespaciada (códigos, IDs)',
    )

    # ─── Geometría ────────────────────────────────────────────
    radius_sm = models.CharField(max_length=10, default='0.5rem', help_text='Radio chico (8px)')
    radius_md = models.CharField(max_length=10, default='0.75rem', help_text='Radio medio (12px)')
    radius_lg = models.CharField(max_length=10, default='1rem', help_text='Radio grande (16px)')
    radius_xl = models.CharField(max_length=10, default='1.5rem', help_text='Radio xl (24px) — cards')

    # ─── Botones (Liquid Glass) ───────────────────────────────
    btn_blur = models.CharField(max_length=10, default='40px', help_text='Backdrop-filter blur en botones lg-btn')
    btn_saturate = models.CharField(max_length=10, default='180%', help_text='Backdrop-filter saturate')
    btn_glass_opacity_dark = models.FloatField(default=0.18, help_text='Opacidad del fondo del botón en oscuro (0-1)')
    btn_glass_opacity_light = models.FloatField(default=0.92, help_text='Opacidad del fondo del botón en claro (0-1)')

    # ─── Sombras ──────────────────────────────────────────────
    shadow_card = models.CharField(
        max_length=255,
        default='0 8px 32px -4px rgba(0,0,0,0.35), 0 2px 8px -2px rgba(0,0,0,0.20)',
        help_text='Sombra de cards (lg-card) — modo oscuro',
    )
    shadow_card_light = models.CharField(
        max_length=255,
        default='0 4px 16px -4px rgba(15,23,42,0.08), 0 1px 4px -1px rgba(15,23,42,0.04)',
        help_text='Sombra de cards en modo claro',
    )

    class Meta:
        verbose_name = 'Design System'
        verbose_name_plural = 'Design System'

    def __str__(self) -> str:
        return f'UIDesignTokens (brand={self.color_brand})'

    def reset_to_defaults(self) -> None:
        """Restaura todos los campos a sus valores `default`."""
        for field in self._meta.get_fields():
            if not getattr(field, 'has_default', None) or field.name in ('id', 'pk', 'created_at', 'updated_at'):
                continue
            if field.has_default():
                setattr(self, field.name, field.get_default())
        self.save()
