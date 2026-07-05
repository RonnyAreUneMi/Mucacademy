"""Diseño 'Geométrico': esquinas chevron con capas, marca de agua y QR en 2da página."""
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white

from .._helpers import (
    register_fonts, get_current_date_text, get_script_font,
    format_body_text, draw_text_block,
)
from .._signatures import draw_signatures_universal
from .._logos import draw_smart_logos, draw_unemi_watermark, draw_certifai_brand


def draw_geometric_wow(c, certificado, width, height, pri, sec, ter, txt):
    """Dibuja un certificado geométrico profesional con chevrons, marca de agua y QR."""
    lote = certificado.batch
    register_fonts()
    SCRIPT_FONT = get_script_font()

    # --- 1. WATERMARK (logo UNEMI tenue al fondo) ---
    draw_unemi_watermark(c, width, height)

    # --- 2. ESQUINAS GEOMÉTRICAS (chevrons con capas) ---
    def draw_corner_professional(origin_x, origin_y, rotation, main_col, acc_col):
        c.saveState()
        c.translate(origin_x, origin_y)
        c.rotate(rotation)

        c.setFillColor(main_col)
        p1 = c.beginPath()
        p1.moveTo(0, 0)
        p1.lineTo(9.0*cm, 0)
        p1.lineTo(7.5*cm, 3.0*cm)
        p1.lineTo(3.0*cm, 3.0*cm)
        p1.lineTo(0, 9.0*cm)
        p1.close()
        c.drawPath(p1, fill=1, stroke=0)

        c.setFillColor(acc_col)
        c.setStrokeColor(white)
        c.setLineWidth(3)
        p2 = c.beginPath()
        p2.moveTo(0, 0)
        p2.lineTo(5.5*cm, 0)
        p2.lineTo(0, 5.5*cm)
        p2.close()
        c.drawPath(p2, fill=1, stroke=1)

        c.setFillColor(main_col)
        p3 = c.beginPath()
        p3.moveTo(6.5*cm, 0.4*cm)
        p3.lineTo(9.0*cm, 0.4*cm)
        p3.lineTo(7.5*cm, 2.6*cm)
        p3.lineTo(5.5*cm, 2.6*cm)
        p3.close()
        c.drawPath(p3, fill=1, stroke=1)

        c.restoreState()

    draw_corner_professional(0, 0, 0, pri, sec)
    draw_corner_professional(width, height, 180, sec, pri)

    # --- 3. LOGOS (admin a la izquierda) + marca CertifAI fija a la derecha ---
    logo_h = 3.5*cm
    logo_y = height - 4.8*cm
    draw_smart_logos(c, lote, 3.0*cm, logo_y, width - 6.0*cm, logo_h, align='left')
    # Marca CertifAI: banda más baja e inset para librar el chevron del ángulo.
    draw_certifai_brand(c, 3.0*cm, height - 4.7*cm, width - 7.0*cm, 1.5*cm)

    # --- 4. CONTENIDO ---
    center_x = width / 2
    y_cursor = logo_y - 0.8*cm

    # A. Título script dorado
    c.setFont(SCRIPT_FONT, 44)
    c.setFillColor(sec)
    c.drawCentredString(center_x, y_cursor, "Otorga el presente Reconocimiento")
    y_cursor -= 1.8*cm

    # B. "a:"
    c.setFont("Times-Italic", 12)
    c.setFillColor(HexColor('#888888'))
    c.drawCentredString(center_x, y_cursor, "a:")
    y_cursor -= 1.4*cm

    # C. Nombre en script grande
    name_font_size = 50 if SCRIPT_FONT == 'GreatVibes' else 36
    c.setFont(SCRIPT_FONT, name_font_size)
    c.setFillColor(HexColor('#1a1a1a'))
    nombre = f"{certificado.first_name} {certificado.last_name}".title()
    c.drawCentredString(center_x, y_cursor, nombre)
    y_cursor -= 2.0*cm

    # D. Body con curso en negrita (auto-ajuste de tamaño según espacio disponible)
    sig_area_top = 5.8*cm
    pre_lines, curso_upper, post_lines = format_body_text(certificado, wrap_width=75)
    total_lines = len(pre_lines) + (1 if curso_upper else 0) + len(post_lines)

    if total_lines * 0.65*cm > (y_cursor - sig_area_top):
        body_font_size, line_height_mm, wrap_w = 12, 5.5, 90
    else:
        body_font_size, line_height_mm, wrap_w = 14, 6.5, 75

    y_cursor = draw_text_block(
        c, certificado, center_x, y_start=y_cursor,
        regular_font='Times-Roman', bold_font='Times-Bold',
        regular_color='#333333', bold_color='#111111',
        font_size=body_font_size, line_height=line_height_mm, wrap_width=wrap_w,
    )

    # --- 5. FIRMAS (helper unificado, línea dorada con círculos) ---
    sig_y_cm = getattr(lote, 'signatures_position', 4.2)
    draw_signatures_universal(c, lote, width, line_color=sec, sig_y=sig_y_cm * cm)

    # --- 6. FECHA (debajo de firmas) ---
    date_y = (sig_y_cm * cm) - 2.0*cm
    c.setFont("Times-Roman", 10)
    c.setFillColor(HexColor('#555555'))
    c.drawRightString(width - 3.5*cm, date_y, get_current_date_text(certificado.course_date))
