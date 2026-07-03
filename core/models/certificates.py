"""Certificate batches and issued certificates."""
import uuid

from django.db import models

from core.base.models import TimestampedModel
from core.managers import CertificateManager, BatchManager

from .catalogs.enums import FACULTY_CHOICES, CertificateTemplate, CertificateKind


class CertificateBatch(TimestampedModel):
    """A batch of certificates generated for a course/event.

    Design inheritance:
      - `customize_design=False` (default) → batch inherits GlobalDesign at
        render time.
      - `customize_design=True` → uses its own design fields below.
    """
    name = models.CharField(max_length=200, verbose_name='Batch name')
    excel_file = models.FileField(upload_to='batches_excel/', null=True, blank=True)
    administrator = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)

    kind = models.CharField(
        max_length=10, choices=CertificateKind.choices,
        default=CertificateKind.COURSE, db_index=True,
        help_text='Course = one event; Program = groups several courses.',
    )
    program = models.ForeignKey(
        'core.Program', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='batches', verbose_name='Programa',
        help_text='Set only for program-certificate batches.',
    )

    faculty = models.CharField(
        max_length=20, choices=FACULTY_CHOICES, default='FACI', db_index=True,
    )

    customize_design = models.BooleanField(
        default=False,
        verbose_name='Customize design for this batch',
        help_text='If on, this batch uses its own design instead of the Global Design.',
    )

    template = models.CharField(
        max_length=20, choices=CertificateTemplate.choices,
        default=CertificateTemplate.GEOMETRIC,
    )
    color_primary = models.CharField(max_length=7, default='#162054', help_text='Primary color (Hex)')
    color_secondary = models.CharField(max_length=7, default='#D4AF37', help_text='Secondary color (Hex)')
    color_tertiary = models.CharField(max_length=7, default='#F3F4F6', help_text='Tertiary/detail color (Hex)')
    color_text = models.CharField(max_length=7, default='#333333', help_text='Text color (Hex)')

    body_text = models.TextField(
        default=(
            "Por haber completado satisfactoriamente el curso de capacitación "
            "continua, demostrando compromiso y excelencia académica. Por su "
            "participación en el seminario '{curso}', contribuyendo de manera "
            "activa y profesional al desarrollo de nuevas competencias."
        ),
        help_text='Main certificate body text',
    )

    # Signature 1 (primary, e.g. Rector)
    signature_inst_1 = models.ForeignKey('core.Signature', on_delete=models.SET_NULL, null=True, blank=True, related_name='batches_slot1', verbose_name='Institutional signature 1')
    signature_name_1 = models.CharField(max_length=100, blank=True, default='', verbose_name='Authority name 1')
    signature_role_1 = models.CharField(max_length=100, blank=True, default='', verbose_name='Authority role 1')
    signature_image_1 = models.TextField(null=True, blank=True, verbose_name='Authority signature 1 (Base64)')

    # Signature 2 (secondary, e.g. Dean)
    signature_inst_2 = models.ForeignKey('core.Signature', on_delete=models.SET_NULL, null=True, blank=True, related_name='batches_slot2', verbose_name='Institutional signature 2')
    signature_name_2 = models.CharField(max_length=100, blank=True, default='', verbose_name='Authority name 2')
    signature_role_2 = models.CharField(max_length=100, blank=True, default='', verbose_name='Authority role 2')
    signature_image_2 = models.TextField(null=True, blank=True, verbose_name='Authority signature 2 (Base64)')

    # Signature 3 (optional)
    signature_inst_3 = models.ForeignKey('core.Signature', on_delete=models.SET_NULL, null=True, blank=True, related_name='batches_slot3', verbose_name='Institutional signature 3')
    signature_name_3 = models.CharField(max_length=100, blank=True, verbose_name='Authority name 3')
    signature_role_3 = models.CharField(max_length=100, blank=True, verbose_name='Authority role 3')
    signature_image_3 = models.TextField(null=True, blank=True, verbose_name='Authority signature 3 (Base64)')

    # Signature 4 (optional)
    signature_inst_4 = models.ForeignKey('core.Signature', on_delete=models.SET_NULL, null=True, blank=True, related_name='batches_slot4', verbose_name='Institutional signature 4')
    signature_name_4 = models.CharField(max_length=100, blank=True, verbose_name='Authority name 4')
    signature_role_4 = models.CharField(max_length=100, blank=True, verbose_name='Authority role 4')
    signature_image_4 = models.TextField(null=True, blank=True, verbose_name='Authority signature 4 (Base64)')

    # Header logos (optional, up to 3)
    header_logo_1 = models.ImageField(upload_to='logos/', null=True, blank=True, verbose_name='Header logo 1')
    header_logo_2 = models.ImageField(upload_to='logos/', null=True, blank=True, verbose_name='Header logo 2')
    header_logo_3 = models.ImageField(upload_to='logos/', null=True, blank=True, verbose_name='Header logo 3')

    signatures_position = models.FloatField(
        default=4.2,
        verbose_name='Vertical signature position (cm)',
        help_text='Distance from the bottom edge. Higher = further up.',
    )

    objects = BatchManager()

    class Meta:
        verbose_name = 'Certificate Batch'
        verbose_name_plural = 'Certificate Batches'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['faculty']),
        ]

    def __str__(self):
        return self.name

    @property
    def active_signatures(self):
        """List of configured signatures (1..4), skipping empty slots.

        A slot is active if it has `signature_inst_N` or a `signature_name_N`.
        Used by the PDF templates.
        """
        signatures = []
        for i in range(1, 5):
            inst = getattr(self, f'signature_inst_{i}')
            name = getattr(self, f'signature_name_{i}', '') or ''
            if inst:
                signatures.append({
                    'slot': i, 'name': inst.name, 'role': inst.role,
                    'image': inst.image,
                })
            elif name.strip():
                signatures.append({
                    'slot': i, 'name': name,
                    'role': getattr(self, f'signature_role_{i}', '') or '',
                    'image': getattr(self, f'signature_image_{i}', '') or '',
                })
        return signatures


class Certificate(TimestampedModel):
    """Individual certificate issued to a participant for a specific course.

    Personal fields (national_id, names, email) are frozen at issue time:
    even if the Participant is later updated, the certificate keeps the
    original data (audit + legal value).
    """
    batch = models.ForeignKey(CertificateBatch, on_delete=models.CASCADE, related_name='certificates')
    participant = models.ForeignKey(
        'core.Participant', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='certificates',
    )
    national_id = models.CharField(max_length=20, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=200, db_index=True)
    phone = models.CharField(max_length=20, null=True, blank=True)

    # Course/event metadata
    course = models.CharField(max_length=255)
    course_date = models.DateField(null=True, blank=True)
    hours = models.IntegerField(default=0)

    # For program certificates: frozen list of the courses (with their skills
    # and hours) that made up the program at issue time. Shape:
    #   [{"name": "SQL", "hours": 20, "skills": ["...", "..."]}, ...]
    # Null/empty for ordinary course certificates.
    program_data = models.JSONField(null=True, blank=True)

    # Security and access
    verification_hash = models.CharField(
        max_length=100, unique=True, default=uuid.uuid4, db_index=True,
    )
    pdf_file = models.FileField(upload_to='certificates_pdf/', null=True, blank=True)

    # Metrics
    download_count = models.IntegerField(default=0)
    search_count = models.IntegerField(default=0)
    last_download_at = models.DateTimeField(null=True, blank=True)

    objects = CertificateManager()

    class Meta:
        verbose_name = 'Certificate'
        verbose_name_plural = 'Certificates'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(hours__gte=0),
                name='certificate_hours_non_negative',
            ),
        ]
        indexes = [
            models.Index(fields=['batch', '-created_at']),
            models.Index(fields=['national_id', 'email']),
        ]

    def __str__(self):
        return f"{self.national_id} - {self.course}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_program(self) -> bool:
        """True if this is a program-level certificate (groups several courses)."""
        return self.batch.kind == CertificateKind.PROGRAM

    @property
    def was_downloaded(self):
        return self.download_count > 0
