"""DEPRECATED: use `from core.services.pdf import generate_certificate_pdf`.

This shim stays for backward compat with existing imports across the codebase.
The real implementation is in core/services/pdf/ (Strategy pattern).
"""
from core.services.pdf import generate_certificate_pdf  # noqa: F401
