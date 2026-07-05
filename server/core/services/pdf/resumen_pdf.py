"""Genera un PDF profesional del Resumen IA de una sesión (Betto).

Estilo visual:
- Inspirado en los emails de CertifAI (líneas accent naranja, tipografía limpia)
- Colores parametrizables desde `UIDesignTokens` (singleton)
- Layout vertical A4 con márgenes generosos
- Tablas para puntos clave, próximos pasos y cuestionario
- Header con wordmark "certifai" en cada página
- Footer con paginación + metadata IA

Uso:
    from core.services.pdf.resumen_pdf import generar_resumen_pdf
    pdf_bytes = generar_resumen_pdf(resumen)  # ResumenSesion instance
    # → bytes listos para HttpResponse(pdf_bytes, content_type='application/pdf')
"""
from __future__ import annotations

import io
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

from core.models import SessionSummary, UIDesignTokens


# ─── Helpers ──────────────────────────────────────────────────────

def _tokens():
    """Obtiene tokens de diseño (con defaults si no existen)."""
    try:
        t = UIDesignTokens.load()
    except Exception:
        t = None
    return {
        'brand':      HexColor(getattr(t, 'color_brand',      None) or '#F58830'),
        'brand_dark': HexColor(getattr(t, 'color_brand_dark', None) or '#D97520'),
        'accent':     HexColor(getattr(t, 'color_accent',     None) or '#162054'),
        'success':    HexColor('#10B981'),
        'success_bg': HexColor('#ECFDF5'),
        'violet':     HexColor('#7C3AED'),
        'violet_bg':  HexColor('#F5F3FF'),
        'danger':     HexColor('#EF4444'),
        'text':       HexColor('#0F172A'),
        'muted':      HexColor('#64748B'),
        'border':     HexColor('#E2E8F0'),
        'soft':       HexColor('#F8FAFC'),
        'white':      HexColor('#FFFFFF'),
    }


def _styles(c):
    """Construye stylesheet usando la paleta `c` (output de _tokens)."""
    ss = getSampleStyleSheet()
    base = 'Helvetica'
    base_b = 'Helvetica-Bold'
    return {
        'h1': ParagraphStyle('h1', parent=ss['Heading1'],
            fontName=base_b, fontSize=22, leading=26,
            textColor=c['text'], spaceBefore=0, spaceAfter=4),
        'h2': ParagraphStyle('h2', parent=ss['Heading2'],
            fontName=base_b, fontSize=13, leading=17,
            textColor=c['text'], spaceBefore=14, spaceAfter=6),
        'eyebrow': ParagraphStyle('eyebrow', parent=ss['Normal'],
            fontName=base_b, fontSize=8, leading=10,
            textColor=c['brand'], spaceBefore=0, spaceAfter=2,
            textTransform='uppercase'),
        'meta': ParagraphStyle('meta', parent=ss['Normal'],
            fontName=base, fontSize=10, leading=14,
            textColor=c['muted']),
        'body': ParagraphStyle('body', parent=ss['Normal'],
            fontName=base, fontSize=10.5, leading=16,
            textColor=c['text'], spaceAfter=8),
        'md_h2': ParagraphStyle('md_h2', parent=ss['Normal'],
            fontName=base_b, fontSize=12, leading=16,
            textColor=c['text'], spaceBefore=10, spaceAfter=4),
        'md_h3': ParagraphStyle('md_h3', parent=ss['Normal'],
            fontName=base_b, fontSize=11, leading=14,
            textColor=c['text'], spaceBefore=8, spaceAfter=3),
        'bullet': ParagraphStyle('bullet', parent=ss['Normal'],
            fontName=base, fontSize=10, leading=14,
            textColor=c['text'], spaceAfter=4),
        'quiz_q': ParagraphStyle('quiz_q', parent=ss['Normal'],
            fontName=base_b, fontSize=11, leading=15,
            textColor=c['text'], spaceAfter=6),
        'quiz_opt': ParagraphStyle('quiz_opt', parent=ss['Normal'],
            fontName=base, fontSize=10, leading=13,
            textColor=c['text']),
        'quiz_correct': ParagraphStyle('quiz_correct', parent=ss['Normal'],
            fontName=base_b, fontSize=10, leading=13,
            textColor=c['success']),
        'quiz_exp': ParagraphStyle('quiz_exp', parent=ss['Normal'],
            fontName=base, fontSize=9.5, leading=13,
            textColor=c['muted'], spaceBefore=4, spaceAfter=0),
        'footer': ParagraphStyle('footer', parent=ss['Normal'],
            fontName=base, fontSize=8, leading=10,
            textColor=c['muted'], alignment=TA_CENTER),
    }


def _markdown_to_flowables(src: str, styles, c):
    """Convierte un Markdown simple a una lista de Flowables de ReportLab.

    Soporta:
      - # / ## / ### como h1/h2/h3
      - **negrita** y *cursiva*
      - bullets con `-` o `*`
      - listas numeradas
      - párrafos separados por línea en blanco
    """
    if not src:
        return []
    flow = []
    lines = src.split('\n')
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        if not line:
            i += 1
            continue

        m3 = re.match(r'^###\s+(.+)$', line)
        if m3:
            flow.append(Paragraph(_inline_md(m3.group(1)), styles['md_h3']))
            i += 1
            continue
        m2 = re.match(r'^##\s+(.+)$', line)
        if m2:
            flow.append(Paragraph(_inline_md(m2.group(1)), styles['md_h2']))
            i += 1
            continue
        m1 = re.match(r'^#\s+(.+)$', line)
        if m1:
            flow.append(Paragraph(_inline_md(m1.group(1)), styles['md_h2']))
            i += 1
            continue

        # Listas
        if re.match(r'^[-*]\s+', line) or re.match(r'^\d+\.\s+', line):
            items = []
            while i < len(lines):
                m = re.match(r'^(?:[-*]|\d+\.)\s+(.+)$', lines[i].strip())
                if not m:
                    break
                items.append(m.group(1))
                i += 1
            for it in items:
                flow.append(Paragraph(
                    f'<font color="{_hex(c["brand"])}"><b>•</b></font>&nbsp;&nbsp;{_inline_md(it)}',
                    styles['bullet']))
            flow.append(Spacer(1, 4))
            continue

        # Párrafo (puede tener varias líneas hasta vacío)
        para_lines = [raw]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^#{1,3}\s+', lines[i].strip()) \
                and not re.match(r'^[-*]\s+', lines[i].strip()) \
                and not re.match(r'^\d+\.\s+', lines[i].strip()):
            para_lines.append(lines[i])
            i += 1
        flow.append(Paragraph(_inline_md(' '.join(l.strip() for l in para_lines)),
                              styles['body']))
    return flow


def _inline_md(text: str) -> str:
    """**bold** y *italic* → <b>/<i> ReportLab."""
    text = _escape_xml(text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', text)
    return text


def _hex(color) -> str:
    """Convierte un HexColor de ReportLab a string CSS `#rrggbb`.

    `HexColor.hexval()` devuelve `'0xrrggbb'`, así que reemplazamos el prefijo.
    Necesario para incrustar en tags `<font color="...">` de Paragraph.
    """
    return '#' + color.hexval()[2:]


def _escape_xml(t: str) -> str:
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _format_fecha(d) -> str:
    if not d:
        return '—'
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
             'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    return f'{d.day} de {meses[d.month - 1]} de {d.year}'


# ─── Header y footer (canvas hook) ───────────────────────────────

class _PageDecorator:
    """Pinta el header y footer en cada página."""

    def __init__(self, palette, doc_title: str):
        self.c = palette
        self.title = doc_title

    def __call__(self, canvas, doc):
        canvas.saveState()
        w, h = A4

        # ─── Top accent line (3pt naranja) ─────────────────────
        canvas.setFillColor(self.c['brand'])
        canvas.rect(0, h - 3 * mm, w, 3 * mm, stroke=0, fill=1)

        # ─── Wordmark "certif[ai]" ─────────────────────────────
        canvas.setFont('Helvetica-Bold', 12)
        canvas.setFillColor(self.c['text'])
        canvas.drawString(20 * mm, h - 13 * mm, 'certif')
        canvas.setFillColor(self.c['brand'])
        certif_w = canvas.stringWidth('certif', 'Helvetica-Bold', 12)
        canvas.drawString(20 * mm + certif_w, h - 13 * mm, 'ai')

        # ─── Etiqueta a la derecha del header ──────────────────
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(self.c['muted'])
        canvas.drawRightString(w - 20 * mm, h - 13 * mm, 'Resumen IA · Betto')

        # ─── Línea divisora bajo el header ─────────────────────
        canvas.setStrokeColor(self.c['border'])
        canvas.setLineWidth(0.5)
        canvas.line(20 * mm, h - 17 * mm, w - 20 * mm, h - 17 * mm)

        # ─── Footer: paginación + branding ─────────────────────
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(self.c['muted'])
        canvas.drawString(20 * mm, 10 * mm,
            'CertifAI · Universidad Estatal de Milagro')
        canvas.drawRightString(w - 20 * mm, 10 * mm,
            f'Página {doc.page}')

        # ─── Línea sobre el footer ─────────────────────────────
        canvas.setStrokeColor(self.c['border'])
        canvas.line(20 * mm, 14 * mm, w - 20 * mm, 14 * mm)

        canvas.restoreState()


# ─── Builders de cada sección ─────────────────────────────────────

def _build_hero(sesion, resumen, styles, c):
    """Bloque hero con eyebrow, título grande y meta del evento."""
    meta_parts = []
    meta_parts.append(f'<b>Fecha:</b> {_format_fecha(sesion.date)}')
    meta_parts.append(
        f'<b>Hora:</b> {sesion.start_time.strftime("%H:%M")}–{sesion.end_time.strftime("%H:%M")}'
    )
    if resumen.duration_minutes:
        meta_parts.append(f'<b>Duración:</b> {resumen.duration_minutes} min')
    if sesion.modality:
        meta_parts.append(f'<b>Modalidad:</b> {sesion.get_modality_display()}')

    return [
        Paragraph('RESUMEN DEL EVENTO', styles['eyebrow']),
        Paragraph(_escape_xml(sesion.title or sesion.day_of_week or 'Sesión'),
                  styles['h1']),
        Spacer(1, 8),
        Paragraph(' &nbsp;&nbsp;·&nbsp;&nbsp; '.join(meta_parts), styles['meta']),
        Spacer(1, 18),
    ]


def _build_resumen_md(resumen_md, styles, c):
    if not resumen_md:
        return []
    return [
        Paragraph('DE QUÉ SE HABLÓ', styles['eyebrow']),
        Paragraph('Resumen ejecutivo', styles['h2']),
        Spacer(1, 4),
        *_markdown_to_flowables(resumen_md, styles, c),
        Spacer(1, 12),
    ]


def _build_puntos_clave(puntos, styles, c):
    if not puntos:
        return []
    # Tabla numerada con badge naranja
    rows = []
    for i, p in enumerate(puntos, 1):
        badge = Paragraph(
            f'<font color="white"><b>{i}</b></font>',
            ParagraphStyle('num', fontName='Helvetica-Bold', fontSize=11,
                           textColor=c['white'], alignment=TA_CENTER, leading=14)
        )
        text = Paragraph(_inline_md(p), styles['bullet'])
        rows.append([badge, text])
    table = Table(rows, colWidths=[10 * mm, 150 * mm], hAlign='LEFT')
    table.setStyle(TableStyle([
        # badge cell
        ('BACKGROUND', (0, 0), (0, -1), c['brand']),
        ('ROUNDEDCORNERS', [3, 3, 3, 3]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (0, -1), 0),
        ('RIGHTPADDING', (0, 0), (0, -1), 0),
        ('TOPPADDING', (0, 0), (0, -1), 4),
        ('BOTTOMPADDING', (0, 0), (0, -1), 4),
        # text cell
        ('LEFTPADDING', (1, 0), (1, -1), 10),
        ('RIGHTPADDING', (1, 0), (1, -1), 6),
        ('TOPPADDING', (1, 0), (1, -1), 6),
        ('BOTTOMPADDING', (1, 0), (1, -1), 6),
        # row separators
        ('LINEBELOW', (0, 0), (-1, -2), 0.3, c['border']),
    ]))
    return [
        Paragraph('HALLAZGOS', styles['eyebrow']),
        Paragraph('Puntos clave', styles['h2']),
        Spacer(1, 4),
        table,
        Spacer(1, 14),
    ]


def _build_proximos_pasos(pasos, styles, c):
    if not pasos:
        return []
    rows = []
    for p in pasos:
        check = Paragraph(
            f'<font color="white"><b>✓</b></font>',
            ParagraphStyle('chk', fontName='Helvetica-Bold', fontSize=11,
                           textColor=c['white'], alignment=TA_CENTER, leading=14)
        )
        text = Paragraph(_inline_md(p), styles['bullet'])
        rows.append([check, text])
    table = Table(rows, colWidths=[10 * mm, 150 * mm], hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), c['success']),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (0, -1), 0),
        ('RIGHTPADDING', (0, 0), (0, -1), 0),
        ('TOPPADDING', (0, 0), (0, -1), 4),
        ('BOTTOMPADDING', (0, 0), (0, -1), 4),
        ('LEFTPADDING', (1, 0), (1, -1), 10),
        ('RIGHTPADDING', (1, 0), (1, -1), 6),
        ('TOPPADDING', (1, 0), (1, -1), 6),
        ('BOTTOMPADDING', (1, 0), (1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -2), 0.3, c['border']),
    ]))
    return [
        Paragraph('ACCIONES', styles['eyebrow']),
        Paragraph('Próximos pasos', styles['h2']),
        Spacer(1, 4),
        table,
        Spacer(1, 14),
    ]


def _build_cuestionario(preguntas, styles, c):
    if not preguntas:
        return []
    flow = [
        Paragraph('REPASO', styles['eyebrow']),
        Paragraph('Cuestionario de repaso', styles['h2']),
        Paragraph(
            'Pon a prueba lo que aprendiste. Las respuestas correctas aparecen marcadas con <b>✓</b>.',
            styles['meta']),
        Spacer(1, 12),
    ]
    for idx, q in enumerate(preguntas, 1):
        block = [
            Paragraph(
                f'<font color="{_hex(c["violet"])}"><b>Pregunta {idx}.</b></font>&nbsp;&nbsp;{_inline_md(q.get("question", ""))}',
                styles['quiz_q']),
        ]
        correct_idx = q.get('correct_idx', -1)
        opciones = q.get('options', [])
        opt_rows = []
        for j, opt in enumerate(opciones):
            letter = chr(65 + j)
            is_correct = (j == correct_idx)
            if is_correct:
                success_color = _hex(c['success'])
                marker = Paragraph(
                    f'<font color="{success_color}"><b>{letter} &#10004;</b></font>',
                    styles['quiz_correct'])
                text = Paragraph(f'<b>{_inline_md(opt)}</b>', styles['quiz_correct'])
                bg = c['success_bg']
            else:
                marker = Paragraph(f'<b>{letter}</b>', styles['quiz_opt'])
                text = Paragraph(_inline_md(opt), styles['quiz_opt'])
                bg = c['soft']
            opt_rows.append([marker, text])

        opt_table = Table(opt_rows, colWidths=[12 * mm, 148 * mm], hAlign='LEFT')
        opt_styles = [
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, -2), 0.3, c['border']),
        ]
        # Fondo verde claro en la opción correcta
        for j in range(len(opciones)):
            if j == correct_idx:
                opt_styles.append(('BACKGROUND', (0, j), (-1, j), c['success_bg']))
        opt_table.setStyle(TableStyle(opt_styles))
        block.append(opt_table)

        # Explicación
        if q.get('explanation'):
            block.append(Paragraph(
                f'<i><b>💡 Por qué:</b> {_inline_md(q["explanation"])}</i>',
                styles['quiz_exp']))
        block.append(Spacer(1, 12))

        flow.append(KeepTogether(block))
    return flow


def _build_footer_metadata(resumen, styles, c):
    parts = []
    if resumen.ai_model:
        parts.append(f'Modelo IA: <b>{resumen.ai_model}</b>')
    if resumen.processed_at:
        parts.append(f'Generado: {resumen.processed_at.strftime("%d/%m/%Y %H:%M")}')
    if resumen.duration_minutes:
        parts.append(f'Duración transcript: {resumen.duration_minutes} min')
    if not parts:
        return []
    return [
        Spacer(1, 16),
        Paragraph(
            f'<font color="{_hex(c["muted"])}">' +
            ' &nbsp;·&nbsp; '.join(parts) + '</font>',
            styles['meta']),
    ]


# ─── Entry point ─────────────────────────────────────────────────

def generar_resumen_pdf(resumen: SessionSummary) -> bytes:
    """Genera el PDF del resumen y devuelve los bytes.

    Args:
        resumen: instancia de SessionSummary en estado READY.

    Returns:
        bytes del PDF listos para enviar como HttpResponse.
    """
    c = _tokens()
    styles = _styles(c)
    sesion = resumen.event

    buf = io.BytesIO()
    title = f'Resumen · {sesion.title or sesion.day_of_week}'
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=24 * mm, bottomMargin=20 * mm,
        title=title, author='CertifAI · Betto IA',
        subject='Resumen IA del evento', creator='CertifAI',
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height - 4 * mm,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id='main',
    )
    decorator = _PageDecorator(c, title)
    doc.addPageTemplates([
        PageTemplate(id='all', frames=[frame], onPage=decorator),
    ])

    story = []
    story.extend(_build_hero(sesion, resumen, styles, c))
    story.extend(_build_resumen_md(resumen.summary_md, styles, c))
    story.extend(_build_puntos_clave(resumen.key_points or [], styles, c))
    story.extend(_build_proximos_pasos(resumen.next_steps or [], styles, c))
    if resumen.quiz:
        story.append(PageBreak())
        story.extend(_build_cuestionario(resumen.quiz, styles, c))
    story.extend(_build_footer_metadata(resumen, styles, c))

    doc.build(story)
    return buf.getvalue()
