import base64
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader

from ._helpers import hex2rgb

def get_signatures_for_lote(lote):
    signatures = []
    for i in range(1, 5):
        firma_inst = getattr(lote, f'signature_inst_{i}')
        if firma_inst:
            signatures.append({
                'name': firma_inst.name,
                'cargo': firma_inst.role,
                'img': firma_inst.image
            })
        else:
            nombre = getattr(lote, f'signature_name_{i}')
            if nombre:
                signatures.append({
                    'name': nombre,
                    'cargo': getattr(lote, f'signature_role_{i}'),
                    'img': getattr(lote, f'signature_image_{i}')
                })
    return signatures


def draw_signatures_bottom(c, lote, width, line_color='#000000', name_color='#222222', cargo_color='#666666', margin_left=None, margin_right=None, sig_y=None):
    """
    Dibuja firmas en la zona inferior del certificado.
    Soporta 1, 2, 3 o 4 firmas distribuidas uniformemente.
    """
    signatures = get_signatures_for_lote(lote)
    num = len(signatures)
    if num == 0:
        return

    SIG_LINE_Y = sig_y if sig_y is not None else 3.8 * cm
    IMG_H = 1.8 * cm            # Alto de imagen de firma
    IMG_W = 3.5 * cm            # Ancho de imagen de firma
    LINE_HALF = 2.8 * cm        # Mitad de la línea de firma
    default_margin = 2.5 * cm
    left = margin_left if margin_left is not None else default_margin
    right = margin_right if margin_right is not None else default_margin

    usable = width - left - right
    spacing = usable / num

    for i, sig in enumerate(signatures):
        cx = left + spacing * i + spacing / 2

        # Imagen de firma (arriba de la línea)
        if sig.get('img'):
            try:
                img_b64 = sig['img']
                missing = len(img_b64) % 4
                if missing:
                    img_b64 += '=' * (4 - missing)
                img_data = base64.b64decode(img_b64)
                img_reader = ImageReader(BytesIO(img_data))
                c.drawImage(img_reader, cx - IMG_W / 2, SIG_LINE_Y + 0.15 * cm,
                            width=IMG_W, height=IMG_H, mask='auto', preserveAspectRatio=True)
            except:
                pass

        # Línea
        c.setStrokeColor(hex2rgb(line_color))
        c.setLineWidth(0.8)
        c.line(cx - LINE_HALF, SIG_LINE_Y, cx + LINE_HALF, SIG_LINE_Y)

        # Nombre
        name_size = 9 if num <= 3 else 7.5
        c.setFont("Times-Bold", name_size)
        c.setFillColor(hex2rgb(name_color))
        c.drawCentredString(cx, SIG_LINE_Y - 0.45 * cm, sig['name'].upper())

        # Cargo
        cargo_size = 7.5 if num <= 3 else 6.5
        c.setFont("Helvetica-Bold", cargo_size)
        c.setFillColor(hex2rgb(cargo_color))
        c.drawCentredString(cx, SIG_LINE_Y - 0.85 * cm, sig['cargo'].upper())


def draw_signatures(c, certificado, width, y_position, color='#000000'):
    """Legacy wrapper - redirige a draw_signatures_bottom."""
    draw_signatures_bottom(c, certificado.batch, width)


def draw_signatures_universal(c, lote, width, line_color=None, name_color='#1a1a1a',
                              cargo_color='#555555', show_decoration=True,
                              sig_y=None, margin_left=3.0, margin_right=3.0):
    """
    Dibuja firmas con un estilo profesional unificado para las 3 plantillas.

    - Imagen de firma arriba de la línea (respeta offset_y y escala por firma).
    - Línea de color configurable (dorado por defecto) con círculos decorativos en los extremos.
    - Nombre en Times-Bold, cargo en Times-Italic.
    - Ordenado: imagen → línea → nombre → cargo.

    Args:
        line_color: HexColor o str hex. Si None, usa dorado #D4AF37.
        show_decoration: True para círculos en los extremos de la línea.
        sig_y: Posición Y de la línea (cm). Default 4.2cm.
        margin_left/right: Márgenes horizontales (cm).
    """
    from reportlab.lib.colors import HexColor as _HexColor

    signatures = get_signatures_for_lote(lote)
    num = len(signatures)
    if num == 0:
        return

    if line_color is None:
        line_color = _HexColor('#D4AF37')
    elif isinstance(line_color, str):
        line_color = hex2rgb(line_color)

    BASE_LINE_Y = sig_y if sig_y is not None else 4.2 * cm
    BASE_IMG_H = 2.0 * cm
    BASE_IMG_W = 3.8 * cm
    LINE_HALF = 3.2 * cm

    margin_l = margin_left * cm
    margin_r = margin_right * cm
    usable = width - margin_l - margin_r
    spacing = usable / num

    for i, sig in enumerate(signatures):
        cx = margin_l + spacing * i + spacing / 2

        sig_num = i + 1
        img_offset_y = getattr(lote, f'signature_{sig_num}_offset_y', 0) * cm
        escala = getattr(lote, f'signature_{sig_num}_scale', 100) / 100.0

        img_h = BASE_IMG_H * escala
        img_w = BASE_IMG_W * escala

        # Imagen
        if sig.get('img'):
            try:
                img_b64 = sig['img']
                missing = len(img_b64) % 4
                if missing:
                    img_b64 += '=' * (4 - missing)
                img_data = base64.b64decode(img_b64)
                img_reader = ImageReader(BytesIO(img_data))
                img_y = BASE_LINE_Y + 0.15 * cm + img_offset_y
                c.drawImage(img_reader, cx - img_w / 2, img_y,
                            width=img_w, height=img_h, mask='auto', preserveAspectRatio=True)
            except Exception:
                pass

        # Línea con decoración
        c.saveState()
        c.setStrokeColor(line_color)
        c.setLineWidth(1.0)
        c.line(cx - LINE_HALF, BASE_LINE_Y, cx + LINE_HALF, BASE_LINE_Y)
        if show_decoration:
            c.setFillColor(line_color)
            c.circle(cx - LINE_HALF, BASE_LINE_Y, 1.5, fill=1, stroke=0)
            c.circle(cx + LINE_HALF, BASE_LINE_Y, 1.5, fill=1, stroke=0)
        c.restoreState()

        # Nombre
        name_text = (sig.get('name') or '').strip()
        if name_text:
            name_size = 9.5 if num <= 3 else 8
            c.setFont("Times-Bold", name_size)
            c.setFillColor(hex2rgb(name_color) if isinstance(name_color, str) else name_color)
            c.drawCentredString(cx, BASE_LINE_Y - 0.5 * cm, name_text)

        # Cargo
        cargo_text = (sig.get('cargo') or '').strip()
        if cargo_text:
            cargo_size = 8 if num <= 3 else 7
            c.setFont("Times-Italic", cargo_size)
            c.setFillColor(hex2rgb(cargo_color) if isinstance(cargo_color, str) else cargo_color)
            if len(cargo_text) > 30 and num >= 3:
                words = cargo_text.upper().split()
                mid = len(words) // 2
                line1 = ' '.join(words[:mid])
                line2 = ' '.join(words[mid:])
                c.drawCentredString(cx, BASE_LINE_Y - 0.9 * cm, line1)
                c.drawCentredString(cx, BASE_LINE_Y - 1.25 * cm, line2)
            else:
                c.drawCentredString(cx, BASE_LINE_Y - 0.9 * cm, cargo_text.upper())


def _draw_geometric_signatures(c, lote, width, pri, sec, sig_y=None):
    """
    Firmas profesionales para la plantilla geométrica.
    - Imagen de firma centrada
    - Línea DEBAJO de la imagen (nunca cruza texto)
    - Nombre en Times-Bold (serif profesional)
    - Cargo en Times-Roman italic
    - Ordenado: imagen → línea → nombre → cargo
    """
    signatures = get_signatures_for_lote(lote)
    num = len(signatures)
    if num == 0:
        return

    BASE_LINE_Y = sig_y if sig_y is not None else 4.2*cm
    BASE_IMG_H = 2.0*cm
    BASE_IMG_W = 3.8*cm
    LINE_HALF = 3.2*cm

    margin_left = 3.0*cm
    margin_right = 3.0*cm
    usable = width - margin_left - margin_right
    spacing = usable / num

    for i, sig in enumerate(signatures):
        cx = margin_left + spacing * i + spacing / 2
        
        # Per-signature adjustments — ONLY affect the image, NOT the line/text
        sig_num = i + 1
        img_offset_y = getattr(lote, f'signature_{sig_num}_offset_y', 0) * cm
        escala = getattr(lote, f'signature_{sig_num}_scale', 100) / 100.0
        
        # Scale image dimensions
        img_h = BASE_IMG_H * escala
        img_w = BASE_IMG_W * escala

        # 1. Signature Image (above the line, position/size adjustable)
        if sig.get('img'):
            try:
                img_b64 = sig['img']
                missing = len(img_b64) % 4
                if missing:
                    img_b64 += '=' * (4 - missing)
                img_data = base64.b64decode(img_b64)
                img_reader = ImageReader(BytesIO(img_data))
                # Image Y = line + small gap + user offset
                img_y = BASE_LINE_Y + 0.15*cm + img_offset_y
                c.drawImage(img_reader, cx - img_w / 2, img_y,
                            width=img_w, height=img_h, mask='auto', preserveAspectRatio=True)
            except:
                pass

        # 2. Signature Line — FIXED position (gold accent with decorative ends)
        c.saveState()
        c.setStrokeColor(sec)
        c.setLineWidth(1.0)
        c.line(cx - LINE_HALF, BASE_LINE_Y, cx + LINE_HALF, BASE_LINE_Y)
        c.setFillColor(sec)
        c.circle(cx - LINE_HALF, BASE_LINE_Y, 1.5, fill=1, stroke=0)
        c.circle(cx + LINE_HALF, BASE_LINE_Y, 1.5, fill=1, stroke=0)
        c.restoreState()

        # 3. Name — FIXED below line
        name_text = sig['name'].strip()
        if name_text:
            name_size = 9.5 if num <= 3 else 8
            c.setFont("Times-Bold", name_size)
            c.setFillColor(HexColor('#1a1a1a'))
            c.drawCentredString(cx, BASE_LINE_Y - 0.5*cm, name_text)

        # 4. Cargo — FIXED below name
        cargo_text = sig.get('cargo', '').strip()
        if cargo_text:
            cargo_size = 8 if num <= 3 else 7
            c.setFont("Times-Italic", cargo_size)
            c.setFillColor(HexColor('#555555'))
            if len(cargo_text) > 30 and num >= 3:
                words = cargo_text.upper().split()
                mid = len(words) // 2
                line1 = ' '.join(words[:mid])
                line2 = ' '.join(words[mid:])
                c.drawCentredString(cx, BASE_LINE_Y - 0.9*cm, line1)
                c.drawCentredString(cx, BASE_LINE_Y - 1.25*cm, line2)
            else:
                c.drawCentredString(cx, BASE_LINE_Y - 0.9*cm, cargo_text.upper())


