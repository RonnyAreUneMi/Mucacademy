import os
# Force Reload Fix for Function Signature Update
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.conf import settings
from datetime import datetime
from io import BytesIO
import base64


# --- FONTS ---
_fonts_registered = False

def _apply_diseno_global(lote):
    """
    Sobrescribe los campos de diseño del lote (en memoria) con los del
    GlobalDesign singleton, para que toda la generación de PDF use el
    diseño global sin tener que tocar cada función.

    Si el lote tiene `customize_design=True`, se usa el diseño propio del lote.
    """
    if getattr(lote, 'customize_design', False):
        return lote

    try:
        from core.models import GlobalDesign
        diseno = GlobalDesign.load()
    except Exception:
        return lote

    lote.template = diseno.template
    lote.color_primary = diseno.color_primary
    lote.color_secondary = diseno.color_secondary
    lote.color_tertiary = diseno.color_tertiary
    lote.color_text = diseno.color_text
    lote.body_text = diseno.body_text

    lote.signature_inst_1 = diseno.signature_inst_1
    lote.signature_inst_2 = diseno.signature_inst_2
    lote.signature_inst_3 = diseno.signature_inst_3
    # Limpiar firmas custom (1-3) — el diseño global solo usa firmas institucionales 1-3
    for i in (1, 2, 3):
        setattr(lote, f'signature_name_{i}', '')
        setattr(lote, f'signature_role_{i}', '')
        setattr(lote, f'signature_image_{i}', '')

    # Firma 4 = la personalizada del diseño global
    lote.signature_inst_4 = None
    lote.signature_name_4 = diseno.signature_name_4 or ''
    lote.signature_role_4 = diseno.signature_role_4 or ''
    lote.signature_image_4 = diseno.signature_image_4 or ''

    lote.header_logo_1 = diseno.header_logo_1
    lote.header_logo_2 = diseno.header_logo_2
    lote.header_logo_3 = diseno.header_logo_3

    lote.signatures_position = diseno.signatures_position

    # Per-signature adjustments
    for i in range(1, 5):
        setattr(lote, f'signature_{i}_offset_y', getattr(diseno, f'signature_{i}_offset_y', 0))
        setattr(lote, f'signature_{i}_scale', getattr(diseno, f'signature_{i}_scale', 100))

    return lote


