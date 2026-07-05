"""Helpers compartidos entre las plantillas PDF: fuentes, colores, formato de texto."""
import os
from datetime import datetime

from django.conf import settings
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


_fonts_registered = False

FONT_FILES = {
    'GreatVibes': 'GreatVibes-Regular.ttf',
    'KaushanScript': 'KaushanScript-Regular.ttf',
    'Pacifico': 'Pacifico-Regular.ttf',
    'Comfortaa-Bold': 'Comfortaa-Bold.ttf',
    'Quicksand-Bold': 'Quicksand-Bold.ttf',
}


def register_fonts():
    """Registra todas las fuentes TTF disponibles en static/fonts/."""
    global _fonts_registered
    if _fonts_registered:
        return
    font_dir = os.path.join(settings.BASE_DIR, 'static', 'fonts')
    for font_name, file_name in FONT_FILES.items():
        path = os.path.join(font_dir, file_name)
        if not os.path.exists(path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(font_name, path))
        except Exception:
            pass
    _fonts_registered = True


def get_script_font(preferred=('GreatVibes', 'KaushanScript', 'Pacifico')):
    """Devuelve la mejor fuente script disponible; cae a Times-Italic si ninguna."""
    register_fonts()
    registered = pdfmetrics.getRegisteredFontNames()
    for name in preferred:
        if name in registered:
            return name
    return 'Times-Italic'


def hex2rgb(hex_code):
    try:
        if not hex_code.startswith('#'):
            hex_code = '#' + hex_code
        return HexColor(hex_code)
    except:
        return HexColor('#000000')


def get_current_date_text(fecha_curso=None):
    fecha = fecha_curso if fecha_curso else datetime.now()
    meses_es = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
    return f"Milagro, {fecha.day} de {meses_es.get(fecha.month, '')} del {fecha.year}"


def draw_text_block(c, certificado, center_x, y_start, *,
                    regular_font='Helvetica', bold_font='Helvetica-Bold',
                    regular_color='#333333', bold_color='#111111',
                    font_size=14, line_height=7, wrap_width=75):
    """
    Dibuja el body del certificado con el nombre del curso en negrita.

    Usa format_body_text() internamente. Devuelve la coordenada Y final
    (útil para seguir dibujando debajo). Los colores y fuentes son configurables
    para cada plantilla.

    Args:
        c: canvas de reportlab.
        center_x, y_start: coordenadas de inicio (centro horizontal / top).
        regular_font/bold_font: nombres de fuente PDF.
        regular_color/bold_color: str hex.
        font_size: tamaño en puntos.
        line_height: altura de línea en mm.
        wrap_width: ancho de wrap en caracteres.

    Returns:
        Y final (útil para continuar dibujando debajo).
    """
    from reportlab.lib.units import mm

    pre_lines, curso_upper, post_lines = format_body_text(certificado, wrap_width=wrap_width)
    line_h = line_height * mm
    y = y_start

    c.setFont(regular_font, font_size)
    c.setFillColor(hex2rgb(regular_color))
    for line in pre_lines:
        c.drawCentredString(center_x, y, line)
        y -= line_h

    if curso_upper:
        c.setFont(bold_font, font_size)
        c.setFillColor(hex2rgb(bold_color))
        c.drawCentredString(center_x, y, curso_upper)
        y -= line_h

    c.setFont(regular_font, font_size)
    c.setFillColor(hex2rgb(regular_color))
    for line in post_lines:
        c.drawCentredString(center_x, y, line)
        y -= line_h

    return y


def format_body_text(certificado, wrap_width=75):
    """
    Procesa el texto del cuerpo reemplazando {curso} y {horas}.
    Devuelve (pre_lines, curso_upper, post_lines) para permitir resaltar el nombre
    del curso en negrita. Si no hay marcador {curso}, todo va en pre_lines.
    """
    from textwrap import wrap
    body_raw = certificado.batch.body_text or ''
    curso_upper = (certificado.batch.name or '').upper()
    horas_str = str(certificado.hours or 0)
    body = body_raw.replace('{horas}', horas_str)

    if '{curso}' in body:
        pre, post = body.split('{curso}', 1)
        pre_lines = wrap(pre.strip(), width=wrap_width) if pre.strip() else []
        post_lines = wrap(post.strip(), width=wrap_width) if post.strip() else []
    else:
        pre_lines = wrap(body.strip(), width=wrap_width)
        curso_upper = ''
        post_lines = []

    return pre_lines, curso_upper, post_lines


