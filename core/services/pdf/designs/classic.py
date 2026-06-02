"""Diseño 'Clásico': marco elegante con esquinas diamante y logos en header."""
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor

from .._helpers import (
    register_fonts, get_current_date_text, get_script_font, draw_text_block,
)
from .._signatures import draw_signatures_universal
from .._logos import draw_smart_logos


def draw_classic_wow(c, certificado, width, height, pri, sec, ter, txt):
    """Dibuja un certificado con estilo clásico (marco doble, diamantes, script)."""
    register_fonts()
    lote = certificado.batch

    TITLE_FONT = "Times-Bold"
    BODY_FONT = "Times-Roman"
    SANS_BOLD = "Helvetica-Bold"
    SCRIPT_FONT = get_script_font()

    # === DECORATIVE ELEMENTS ===

    # 1. Ribbon Background (Top Right)
    c.saveState()
    c.translate(width - 60*mm, height - 40*mm)
    c.rotate(18)
    c.setFillColor(pri, alpha=0.08)
    c.roundRect(-110*mm, -60*mm, 220*mm, 120*mm, 30*mm, fill=1, stroke=0)
    c.setFillColor(sec, alpha=0.05)
    c.roundRect(-110*mm, -60*mm, 220*mm, 120*mm, 30*mm, fill=1, stroke=0)
    c.restoreState()

    # 2. Frames (Refined)
    margin_frame = 10*mm
    frame_w = width - 2 * margin_frame
    frame_h = height - 2 * margin_frame

    c.saveState()
    c.setStrokeColor(pri, alpha=0.55)
    c.setLineWidth(3)
    c.roundRect(margin_frame, margin_frame, frame_w, frame_h, 3*mm, fill=0, stroke=1)

    margin_inner = 16*mm
    inner_w = width - 2 * margin_inner
    inner_h = height - 2 * margin_inner
    c.setStrokeColor(sec, alpha=0.7)
    c.setLineWidth(1.5)
    c.roundRect(margin_inner, margin_inner, inner_w, inner_h, 2.5*mm, fill=0, stroke=1)
    c.restoreState()

    # 3. Corner Diamond Ornaments
    c.saveState()
    diamond_size = 4*mm
    corners = [
        (margin_inner, margin_inner),
        (width - margin_inner, margin_inner),
        (margin_inner, height - margin_inner),
        (width - margin_inner, height - margin_inner),
    ]
    for cx_d, cy_d in corners:
        c.setFillColor(sec)
        p = c.beginPath()
        p.moveTo(cx_d, cy_d + diamond_size)
        p.lineTo(cx_d + diamond_size, cy_d)
        p.lineTo(cx_d, cy_d - diamond_size)
        p.lineTo(cx_d - diamond_size, cy_d)
        p.close()
        c.drawPath(p, fill=1, stroke=0)
        inner_d = diamond_size * 0.5
        c.setFillColor(pri)
        p2 = c.beginPath()
        p2.moveTo(cx_d, cy_d + inner_d)
        p2.lineTo(cx_d + inner_d, cy_d)
        p2.lineTo(cx_d, cy_d - inner_d)
        p2.lineTo(cx_d - inner_d, cy_d)
        p2.close()
        c.drawPath(p2, fill=1, stroke=0)
    c.restoreState()

    # === HEADER LOGOS (helper unificado con defaults muc/unemi/feue) ===
    logo_h = 2.8*cm
    logo_area_y = height - 16*mm - logo_h
    draw_smart_logos(c, lote, margin_inner, logo_area_y, inner_w, logo_h, align='center')

    # === MAIN CONTENT ===
    main_y_start = height - 75*mm
    center_x = width / 2

    c.setFont(TITLE_FONT, 38)
    c.setFillColor(HexColor('#D4AF37'))
    c.drawCentredString(center_x, main_y_start, "CERTIFICADO")

    c.setFont(SANS_BOLD, 11)
    c.setFillColor(HexColor("#1c1c1cb8"))
    c.drawCentredString(center_x, main_y_start - 10*mm, "DE ASISTENCIA Y APROBACIÓN")

    c.setFont(BODY_FONT, 13)
    c.setFillColor(HexColor("#1c1c1cc7"))
    c.drawCentredString(center_x, main_y_start - 22*mm, "Se otorga el presente certificado a:")

    # Nombre (fuente script)
    name_font_size = 48 if SCRIPT_FONT == 'GreatVibes' else 36
    c.setFont(SCRIPT_FONT, name_font_size)
    c.setFillColor(txt)
    name_y = main_y_start - 38*mm
    nombre = f"{certificado.first_name} {certificado.last_name}".title()
    c.drawCentredString(center_x, name_y, nombre)

    # Body con curso en negrita
    draw_text_block(
        c, certificado, center_x, y_start=name_y - 20*mm,
        regular_color='#000000', bold_color='#000000',
        font_size=14, line_height=7,
    )

    # Fecha
    c.setFont("Times-Italic", 13)
    c.setFillColor(HexColor('#777777'))
    c.drawRightString(width - 2.5*cm, 2.0*cm, get_current_date_text(certificado.course_date))

    # Firmas unificadas (línea dorada con círculos)
    draw_signatures_universal(c, lote, width, line_color=sec, sig_y=4.5*cm)
