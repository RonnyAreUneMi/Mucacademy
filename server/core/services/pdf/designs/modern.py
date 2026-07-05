"""Diseño 'Moderno': barra lateral con sello dorado y logos inline."""
import math
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white

from .._helpers import (
    register_fonts, get_current_date_text, get_script_font, draw_text_block,
)
from .._signatures import draw_signatures_universal
from .._logos import draw_smart_logos, draw_certifai_brand


def draw_modern_wow(c, certificado, width, height, pri, sec, ter, txt):
    """Dibuja un certificado con estilo moderno (barra lateral + sello de roseta)."""
    register_fonts()
    lote = certificado.batch
    SCRIPT_FONT = get_script_font()

    # --- SIDEBAR DECORATION ---
    c.saveState()
    c.setFillColor(pri)
    c.rect(0, 0, 3.5*cm, height, fill=1, stroke=0)

    c.setFillColor(pri)
    c.saveState()
    c.translate(0, height)
    c.rotate(-45)
    c.roundRect(-2*cm, -5*cm, 10*cm, 10*cm, 1*cm, fill=1, stroke=0)
    c.restoreState()

    c.setFillColor(pri, alpha=0.7)
    c.saveState()
    c.translate(0, height * 0.55)
    c.rotate(-45)
    c.roundRect(-4*cm, -5*cm, 11*cm, 11*cm, 1.5*cm, fill=1, stroke=0)
    c.restoreState()

    c.setFillColor(pri)
    c.saveState()
    c.translate(0, 0)
    c.rotate(-45)
    c.roundRect(-2*cm, -3*cm, 12*cm, 12*cm, 1*cm, fill=1, stroke=0)
    c.restoreState()
    c.restoreState()

    # --- GOLD SEAL ---
    seal_x = 4.5*cm
    seal_y = height - 4.5*cm
    seal_radius = 1.6*cm

    c.saveState()
    c.translate(seal_x, seal_y)

    c.setFillColor(sec)
    path_ribbon = c.beginPath()
    path_ribbon.moveTo(-0.8*cm, -1*cm); path_ribbon.lineTo(-1.2*cm, -3.5*cm); path_ribbon.lineTo(-0.6*cm, -2.8*cm); path_ribbon.lineTo(0, -3.5*cm); path_ribbon.lineTo(0, -1*cm); path_ribbon.close()

    path_ribbon2 = c.beginPath()
    path_ribbon2.moveTo(0.8*cm, -1*cm); path_ribbon2.lineTo(1.2*cm, -3.5*cm); path_ribbon2.lineTo(0.6*cm, -2.8*cm); path_ribbon2.lineTo(0, -3.5*cm); path_ribbon2.lineTo(0, -1*cm); path_ribbon2.close()

    c.drawPath(path_ribbon, fill=1, stroke=0)
    c.drawPath(path_ribbon2, fill=1, stroke=0)

    # Rosette
    c.setFillColor(sec)
    points = 24
    outer_r = seal_radius; inner_r = seal_radius * 0.85
    p = c.beginPath()
    for i in range(2 * points + 1):
        angle = math.pi * i / points
        r = outer_r if i % 2 == 0 else inner_r
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        if i == 0: p.moveTo(x, y)
        else: p.lineTo(x, y)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    c.setFillColor(white, alpha=0.3)
    c.circle(0, 0, seal_radius*0.7, fill=1, stroke=0)
    c.setStrokeColor(white); c.setLineWidth(2)
    c.circle(0, 0, seal_radius*0.6, fill=0, stroke=1)
    c.restoreState()

    # --- MAIN CONTENT ---
    margin_left = 6.5*cm
    content_width = width - margin_left - 1.5*cm
    center_x = margin_left + (content_width / 2)

    # Logos (admin a la izquierda) + marca CertifAI fija a la derecha
    draw_smart_logos(c, lote, margin_left, height - 3*cm, content_width, 2.2*cm, align='left')
    draw_certifai_brand(c, margin_left, height - 3*cm, content_width, 2.2*cm)

    y_cursor = height - 5*cm

    c.setFont("Times-Bold", 42)
    c.setFillColor(HexColor('#111111'))
    c.drawCentredString(center_x, y_cursor, "CERTIFICADO")
    y_cursor -= 1.2*cm

    c.setFont("Helvetica", 14)
    c.setFillColor(sec)
    c.drawCentredString(center_x, y_cursor, "DE RECONOCIMIENTO")
    y_cursor -= 1.5*cm

    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(HexColor('#555555'))
    c.drawCentredString(center_x, y_cursor, "Otorgado a:")
    y_cursor -= 1.8*cm

    name_size = 52 if SCRIPT_FONT == 'GreatVibes' else 36
    c.setFont(SCRIPT_FONT, name_size)
    c.setFillColor(HexColor('#111111'))
    nombre = f"{certificado.first_name} {certificado.last_name}".title()
    c.drawCentredString(center_x, y_cursor, nombre)

    c.setStrokeColor(sec); c.setLineWidth(1.5)
    name_width = c.stringWidth(nombre, SCRIPT_FONT, name_size)
    line_w = max(name_width * 1.2, 12*cm)
    c.line(center_x - line_w/2, y_cursor - 2, center_x + line_w/2, y_cursor - 2)
    y_cursor -= 2.2*cm

    # Body con curso en negrita
    y_cursor = draw_text_block(
        c, certificado, center_x, y_start=y_cursor,
        regular_color='#555555', bold_color='#111111',
        font_size=11, line_height=6,
    )
    y_cursor -= 8*mm

    # Fecha
    c.setFont("Times-Italic", 13)
    c.setFillColor(HexColor('#777777'))
    c.drawRightString(width - 2.5*cm, 2.0*cm, get_current_date_text(certificado.course_date))

    # Firmas unificadas (respetan el sidebar)
    draw_signatures_universal(c, lote, width, line_color=sec,
                              margin_left=6.5, margin_right=1.5, sig_y=3.8*cm)
