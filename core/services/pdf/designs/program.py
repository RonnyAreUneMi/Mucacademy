"""Diseño 'Programa': certificado que agrupa varios cursos y sus competencias.

Lista cada curso del programa con sus habilidades y las horas totales, y
respeta el diseño elegido (Clásico / Moderno / Geométrico): el borde y la
disposición cambian según la plantilla.
"""
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit

from .._helpers import register_fonts, get_current_date_text, get_script_font
from .._signatures import draw_signatures_universal
from .._logos import draw_smart_logos, draw_unemi_watermark, draw_certifai_brand
from .._qr import _border_classic, _border_modern, _border_geometric


def draw_program_wow(c, certificado, width, height, pri, sec, ter, txt, template='classic'):
    """Certificado de programa con el borde/estilo de la plantilla elegida."""
    register_fonts()
    lote = certificado.batch

    TITLE_FONT = "Times-Bold"
    BODY_FONT = "Times-Roman"
    SANS_BOLD = "Helvetica-Bold"
    SANS = "Helvetica"
    SCRIPT_FONT = get_script_font()

    # === Borde según el diseño + márgenes de contenido ===
    margin_right = 16*mm
    if template == 'modern':
        _border_modern(c, width, height, pri, sec)
        content_left = 5.0*cm          # deja espacio a la barra lateral
        sig_margins = dict(margin_left=6.5, margin_right=1.5)
    elif template == 'geometric':
        draw_unemi_watermark(c, width, height)   # fondo UNEMI (igual que el geométrico)
        _border_geometric(c, width, height, pri, sec)
        content_left = 16*mm
        sig_margins = {}
    else:  # classic
        _border_classic(c, width, height, pri, sec)
        content_left = 16*mm
        sig_margins = {}

    content_right = width - margin_right
    inner_w = content_right - content_left
    center_x = (content_left + content_right) / 2

    # === Logos header (admin a la izquierda) + marca CertifAI fija a la derecha ===
    logo_h = 2.5*cm
    logo_area_y = height - 15*mm - logo_h
    draw_smart_logos(c, lote, content_left, logo_area_y, inner_w, logo_h, align='left')
    draw_certifai_brand(c, content_left, logo_area_y, inner_w, logo_h)

    main_y = height - 62*mm

    c.setFont(TITLE_FONT, 34)
    c.setFillColor(HexColor('#D4AF37'))
    c.drawCentredString(center_x, main_y, "CERTIFICADO DE PROGRAMA")

    c.setFont(BODY_FONT, 12)
    c.setFillColor(HexColor("#1c1c1cc7"))
    c.drawCentredString(center_x, main_y - 9*mm, "Se otorga el presente certificado a:")

    # Nombre (script)
    name_font_size = 42 if SCRIPT_FONT == 'GreatVibes' else 32
    c.setFont(SCRIPT_FONT, name_font_size)
    c.setFillColor(txt)
    name_y = main_y - 23*mm
    nombre = f"{certificado.first_name} {certificado.last_name}".title()
    c.drawCentredString(center_x, name_y, nombre)

    # Intro del programa
    program_name = (certificado.course or '').title()
    total_hours = certificado.hours or 0
    intro = (
        f"Por haber culminado satisfactoriamente el programa “{program_name}”, "
        f"con un total de {total_hours} horas académicas, que comprende:"
    )
    c.setFont(BODY_FONT, 12.5)
    c.setFillColor(HexColor("#000000"))
    y = name_y - 12*mm
    for line in simpleSplit(intro, BODY_FONT, 12.5, inner_w - 20*mm):
        c.drawCentredString(center_x, y, line)
        y -= 6*mm

    # === Tabla de cursos + habilidades ===
    courses = certificado.program_data or []
    left_x = content_left + 14*mm
    text_w = inner_w - 28*mm
    y -= 4*mm

    # Espaciado adaptativo: si hay muchos cursos, comprime.
    n = max(1, len(courses))
    header_size = 12 if n <= 4 else 10.5
    skill_size = 10 if n <= 4 else 9
    line_h = 5.2*mm if n <= 4 else 4.4*mm

    for course in courses:
        cname = course.get('name', '') or ''
        chours = course.get('hours', 0) or 0
        skills = course.get('skills', []) or []

        c.setFillColor(sec)
        c.circle(left_x - 3*mm, y + 1.2*mm, 1.1*mm, fill=1, stroke=0)
        c.setFont(SANS_BOLD, header_size)
        c.setFillColor(pri)
        head = f"{cname}" + (f"  ·  {chours} h" if chours else "")
        c.drawString(left_x, y, head)
        y -= line_h

        if skills:
            skills_text = "Habilidades: " + " · ".join(str(s) for s in skills)
            c.setFont(SANS, skill_size)
            c.setFillColor(HexColor('#444444'))
            for line in simpleSplit(skills_text, SANS, skill_size, text_w):
                c.drawString(left_x, y, line)
                y -= line_h
        y -= 2*mm

    # Fecha
    c.setFont("Times-Italic", 12)
    c.setFillColor(HexColor('#777777'))
    c.drawRightString(content_right, 2.0*cm, get_current_date_text(certificado.course_date))

    # Firmas (respetan la barra lateral en 'modern')
    draw_signatures_universal(c, lote, width, line_color=sec, sig_y=3.6*cm, **sig_margins)
