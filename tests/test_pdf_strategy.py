"""Tests del Strategy pattern de generación de PDFs."""
import pytest


@pytest.mark.django_db
class TestPDFStrategy:
    def test_registry_has_expected_designs(self):
        from core.services.pdf.designs import DESIGN_REGISTRY
        assert set(DESIGN_REGISTRY.keys()) == {'classic', 'modern', 'geometric', 'program'}

    def test_get_design_resolves_each(self):
        from core.services.pdf.designs import get_design
        assert get_design('classic').__name__ == 'draw_classic_wow'
        assert get_design('modern').__name__ == 'draw_modern_wow'
        assert get_design('geometric').__name__ == 'draw_geometric_wow'
        assert get_design('program').__name__ == 'draw_program_wow'

    def test_get_design_falls_back_to_classic(self):
        from core.services.pdf.designs import get_design
        assert get_design('unknown').__name__ == 'draw_classic_wow'

    @pytest.mark.parametrize('template', ['classic', 'modern', 'geometric'])
    def test_generate_pdf_produces_bytes(self, certificate, template):
        """Cada Strategy produce un PDF no vacío."""
        certificate.batch.template = template
        certificate.batch.save()
        from core.services.pdf import generate_certificate_pdf
        buf = generate_certificate_pdf(certificate)
        data = buf.getvalue()
        assert len(data) > 1000
        assert data[:4] == b'%PDF'

    def test_shim_still_works(self):
        """El import antiguo sigue funcionando (backward compat)."""
        from core.services.pdf_service import generate_certificate_pdf
        assert callable(generate_certificate_pdf)
