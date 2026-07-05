"""Certificate PDF generation — Strategy pattern.

Usage:
    from core.services.pdf import generate_certificate_pdf

Add a new design:
    1. Create core/services/pdf/designs/<name>.py with a `draw_<name>_wow` function
    2. Register it in core/services/pdf/designs/__init__.py
"""
from .generator import generate_certificate_pdf

__all__ = ['generate_certificate_pdf']
