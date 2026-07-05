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


def draw_unemi_watermark(c, width, height):
    """Marca de agua tenue (logo UNEMI) al fondo, centrada abajo.

    Elemento de branding del diseño (no es un logo de header configurable).
    """
    path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo-unemi-removebg-preview.png')
    if not os.path.exists(path):
        return
    c.saveState()
    c.setFillAlpha(0.08)
    c.setStrokeAlpha(0.08)
    w_img = width * 1.18
    h_img = w_img * 0.28
    x_img = (width - w_img) / 2
    y_img = -1.5 * cm
    try:
        c.drawImage(path, x_img, y_img, width=w_img, height=h_img,
                    mask='auto', preserveAspectRatio=True, anchor='c')
    except Exception:
        pass
    c.restoreState()


def draw_certifai_brand(c, x_start, y_start, max_w, max_h):
    """Marca CertifAI FIJA (tigre + wordmark) alineada a la derecha del header.

    No es configurable: siempre aparece en el lado derecho de todo certificado.
    Estilo del header: 'Certif' en navy + 'AI' en naranja (C y A mayúsculas).
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.colors import HexColor

    NAVY = HexColor('#162054')
    ORANGE = HexColor('#F58830')

    brand_font = 'Helvetica-Bold'
    try:
        if 'Comfortaa-Bold' not in pdfmetrics.getRegisteredFontNames():
            font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Comfortaa-Bold.ttf')
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('Comfortaa-Bold', font_path))
        if 'Comfortaa-Bold' in pdfmetrics.getRegisteredFontNames():
            brand_font = 'Comfortaa-Bold'
    except Exception:
        pass

    right = x_start + max_w - 0.35 * cm      # pequeño respiro respecto al borde
    tiger_size = min(max_h, 1.45 * cm)
    tiger_path = os.path.join(settings.BASE_DIR, 'static', 'tiger_chase_loader.png')

    # Tigre al extremo derecho
    tx = right - tiger_size
    ty = y_start + (max_h - tiger_size) / 2
    if os.path.exists(tiger_path):
        try:
            c.drawImage(tiger_path, tx, ty, width=tiger_size, height=tiger_size,
                        mask='auto', preserveAspectRatio=True)
        except Exception:
            pass

    # Wordmark "CertifAI" a la izquierda del tigre
    fs = 15
    w_certif = c.stringWidth('Certif', brand_font, fs)
    w_ai = c.stringWidth('AI', brand_font, fs)
    text_y = y_start + (max_h - fs) / 2 + 3
    ai_x = tx - 5 - w_ai
    certif_x = ai_x - w_certif
    c.setFont(brand_font, fs)
    c.setFillColor(NAVY)
    c.drawString(certif_x, text_y, 'Certif')
    c.setFillColor(ORANGE)
    c.drawString(ai_x, text_y, 'AI')


def draw_smart_logos(c, lote, x_start, y_start, max_w, max_h, align='center'):
    """
    Draws up to 3 logos configured on the batch/GlobalDesign.
    NO hay logos por defecto: si el lote no tiene logos, no se dibuja ninguno.
    """
    # helper: usa SOLO el logo configurado (sin defaults hardcodeados).
    def get_path(field):
        path = None
        if field:
            if hasattr(field, 'path'):
                path = field.path
            elif isinstance(field, str):
                path = field
        if path and os.path.exists(path):
            return path
        return None

    # Load 3 slots (solo los configurados)
    l1 = get_path(lote.header_logo_1)
    l2 = get_path(lote.header_logo_2)
    l3 = get_path(lote.header_logo_3)

    # Filter valid ones
    active_logos = [l for l in [l1, l2, l3] if l]
    count = len(active_logos)
    
    if count == 0: return # Nothing to draw
    
    # 2. Calculate Positions
    logo_w = max_h * 1.8 # aspect ratio roughly
    # If logos are squarish, this might be too wide, but standard headers are usually wide.
    # Let's verify per image aspect ratio? For now fixed box is safer.
    
    # Spacing
    # If Center: Start from center of max_w
    # If Right: Start from right edge
    
    # Effective width needed
    gap = 1*cm
    total_w = (count * logo_w) + ((count - 1) * gap)
    
    start_x = x_start
    
    if align == 'center':
        start_x = x_start + (max_w - total_w) / 2
    elif align == 'right':
        start_x = x_start + max_w - total_w
    elif align == 'left':
        start_x = x_start
        
    # Draw
    current_x = start_x
    for path in active_logos:
        try:
            c.drawImage(path, current_x, y_start, width=logo_w, height=max_h, mask='auto', preserveAspectRatio=True)
        except: pass
        current_x += (logo_w + gap)


