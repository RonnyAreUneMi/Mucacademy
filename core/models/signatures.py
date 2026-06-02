"""Institutional signatures and the global certificate design (singleton).

Note: signature slots 1..4 are kept as repeated columns (legacy structure,
just translated). Normalizing them into a pivot table is a planned follow-up.
"""
from django.db import models

from core.base.models import SingletonModel

from .catalogs.enums import CertificateTemplate


class Signature(models.Model):
    """Authority signature (rector, dean, etc.) reusable across certificates."""
    name = models.CharField(max_length=100, verbose_name='Authority name', blank=True)
    role = models.CharField(max_length=100, verbose_name='Role')
    image = models.TextField(verbose_name='Signature (Base64)', blank=True, default='')
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Default order')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Signature'
        verbose_name_plural = 'Signatures'

    def __str__(self):
        return f"{self.name} ({self.role})"


class GlobalDesign(SingletonModel):
    """GLOBAL design configuration for all certificates (singleton, pk=1).

    Batches with `customize_design=False` inherit these values at render time.
    """
    template = models.CharField(
        max_length=20, choices=CertificateTemplate.choices,
        default=CertificateTemplate.CLASSIC,
    )
    color_primary = models.CharField(max_length=7, default='#162054')
    color_secondary = models.CharField(max_length=7, default='#D4AF37')
    color_tertiary = models.CharField(max_length=7, default='#F3F4F6')
    color_text = models.CharField(max_length=7, default='#333333')

    body_text = models.TextField(
        default=(
            "Por haber completado satisfactoriamente el curso de capacitación "
            "continua, demostrando compromiso y excelencia académica. Por su "
            "participación en el seminario '{curso}', contribuyendo de manera "
            "activa y profesional al desarrollo de nuevas competencias."
        ),
    )

    signature_inst_1 = models.ForeignKey(
        Signature, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='design_slot1',
    )
    signature_inst_2 = models.ForeignKey(
        Signature, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='design_slot2',
    )
    signature_inst_3 = models.ForeignKey(
        Signature, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='design_slot3',
    )

    # Custom (free-text) signature
    signature_name_4 = models.CharField(max_length=100, blank=True, default='')
    signature_role_4 = models.CharField(max_length=100, blank=True, default='')
    signature_image_4 = models.TextField(blank=True, default='')

    header_logo_1 = models.ImageField(upload_to='logos/', null=True, blank=True)
    header_logo_2 = models.ImageField(upload_to='logos/', null=True, blank=True)
    header_logo_3 = models.ImageField(upload_to='logos/', null=True, blank=True)

    signatures_position = models.FloatField(
        default=4.2,
        verbose_name='Vertical signature position (cm)',
        help_text='Distance from the bottom edge in cm. Higher = further up.',
    )

    # Per-signature adjustments (offset_y in cm, scale in %)
    signature_1_offset_y = models.FloatField(default=0, help_text='Vertical offset signature 1 (cm)')
    signature_1_scale = models.FloatField(default=100, help_text='Scale signature 1 (%)')
    signature_2_offset_y = models.FloatField(default=0, help_text='Vertical offset signature 2 (cm)')
    signature_2_scale = models.FloatField(default=100, help_text='Scale signature 2 (%)')
    signature_3_offset_y = models.FloatField(default=0, help_text='Vertical offset signature 3 (cm)')
    signature_3_scale = models.FloatField(default=100, help_text='Scale signature 3 (%)')
    signature_4_offset_y = models.FloatField(default=0, help_text='Vertical offset signature 4 (cm)')
    signature_4_scale = models.FloatField(default=100, help_text='Scale signature 4 (%)')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Global Design'
        verbose_name_plural = 'Global Design'

    def __str__(self):
        return f"Global Design ({self.get_template_display()})"
