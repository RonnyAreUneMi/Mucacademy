"""Orchestrator — elige Strategy según `lote.plantilla`."""
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from ._diseno import _apply_diseno_global
from ._helpers import hex2rgb
from ._qr import _draw_geometric_verification_page
from .designs import get_design

# Default colors (fallback si el lote no los define)
DEFAULT_COLORS = {
    'pri': HexColor('#0B3D91'),
    'sec': HexColor('#D4AF37'),
    'ter': HexColor('#F3F4F6'),
    'txt': HexColor('#1c1c1c'),
}


def _build_colors(lote):
    """Construye la tupla (pri, sec, ter, txt) respetando custom colors del lote."""
    pri, sec, ter, txt = DEFAULT_COLORS['pri'], DEFAULT_COLORS['sec'], DEFAULT_COLORS['ter'], DEFAULT_COLORS['txt']
    try:
        if lote.color_primary:
            pri = hex2rgb(lote.color_primary)
        if lote.color_secondary:
            sec = hex2rgb(lote.color_secondary)
        if lote.color_tertiary:
            ter = hex2rgb(lote.color_tertiary)
        if lote.color_text:
            txt = hex2rgb(lote.color_text)
    except Exception:
        pass
    return pri, sec, ter, txt


def generate_certificate_pdf(certificado):
    """Genera el PDF del certificado aplicando la plantilla configurada.

    Flujo:
      1. Aplica GlobalDesign al lote si `customize_design=False`.
      2. Determina la plantilla y resuelve la función Strategy.
      3. Delega el dibujo al diseño correspondiente.
      4. Agrega segunda página de verificación si es 'geometric'.
    """
    _apply_diseno_global(certificado.batch)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    plantilla = certificado.batch.template
    pri, sec, ter, txt = _build_colors(certificado.batch)

    # Los certificados de programa usan siempre el diseño 'program'
    # (lista de cursos + competencias), sin importar la plantilla elegida.
    if certificado.batch.kind == 'program':
        plantilla = 'program'

    # Strategy dispatch
    draw_fn = get_design(plantilla)
    draw_fn(c, certificado, width, height, pri, sec, ter, txt)

    # Geometric tiene segunda página con QR
    if plantilla == 'geometric':
        c.showPage()
        _draw_geometric_verification_page(c, certificado, width, height, pri, sec)
    else:
        # Footer de validación (plantilla classic/modern)
        c.setFont('Helvetica', 6)
        c.setFillColor(HexColor('#999999'))
        validation_text = f'ID: {certificado.verification_hash} - Documento generado electrónicamente'
        c.drawCentredString(width / 2, 0.8 * cm, validation_text)

    c.save()
    buffer.seek(0)
    return buffer
