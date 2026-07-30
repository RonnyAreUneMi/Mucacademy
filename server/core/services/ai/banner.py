"""Generación de banners de evento con IA + branding fijo UNEMI.

Flujo:
  1. La IA (OpenAI DALL·E) genera SOLO un fondo temático según el título del
     evento + un prompt ajustable. Se le pide explícitamente que NO escriba
     texto ni logos (la IA no los renderiza bien).
  2. Con Pillow superponemos el branding real garantizado: logo UNEMI, la
     mascota (tigre), el título del evento y el wordmark institucional.

Así el branding siempre es consistente y legible, y cada evento tiene un
fondo único acorde a su tema.
"""
from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from django.conf import settings

from .client import get_runtime_for

# Lienzo final del banner (recomendado en el form: 1200x600).
CANVAS_W, CANVAS_H = 1200, 600

# Colores institucionales.
NAVY = (11, 18, 40)
ORANGE = (245, 136, 48)
WHITE = (255, 255, 255)

# Assets de branding (rutas en static/).
_STATIC = Path(settings.BASE_DIR) / 'static'
LOGO_PATH = _STATIC / 'img' / 'logo-unemi-removebg-preview.png'
TIGER_PATH = _STATIC / 'tiger_chase_loader.png'
FONT_TITLE = _STATIC / 'fonts' / 'Comfortaa-Bold.ttf'
FONT_BODY = _STATIC / 'fonts' / 'Quicksand-Bold.ttf'


def build_prompt(title: str, custom: str = '') -> str:
    """Arma el prompt para la IA.

    Fuerza SIEMPRE un fondo institucional oscuro (azul marino UNEMI) con gráficos
    del tema en la paleta UNEMI (azul + naranja), integrados al fondo, sin ningún
    cuadro/tarjeta blanca, sin texto ni logos (el branding real lo componemos aparte).
    """
    from .prompts import get_prompt
    tema = custom.strip() or title.strip()
    style = get_prompt('banner')
    return (
        'Ilustración horizontal para el banner de un evento académico universitario, '
        'estilo moderno, plano/vectorial, elegante y profesional. '
        f'Tema visual: {tema}. '
        'FONDO obligatorio: azul marino MUY oscuro institucional (entre #0A1535 y '
        '#162054), uniforme y envolvente, atmósfera tecnológica y educativa. '
        'Sobre ese fondo oscuro coloca gráficos e íconos abstractos relacionados con '
        'el tema (líneas, formas geométricas, elementos con brillo suave), en la '
        'paleta institucional: acentos naranja (#F58830) y azules, integrados al '
        'fondo — NADA de cuadros, tarjetas ni recuadros blancos. Concentra los '
        'gráficos hacia la derecha y deja la mitad izquierda más despejada. '
        f'{style} '
        'MUY IMPORTANTE: el fondo debe ser SIEMPRE oscuro (nunca blanco ni claro), '
        'sin ningún rectángulo/tarjeta blanca, sin texto, sin letras, sin palabras, '
        'sin logos, sin marcas de agua, sin personas mirando a cámara.'
    )


def _generate_background(prompt: str) -> bytes:
    """Llama a OpenAI DALL·E y devuelve los bytes PNG del fondo.

    Lanza NotImplementedError si no hay IA configurada o el proveedor no
    soporta imágenes (solo OpenAI).
    """
    rt = get_runtime_for('openai')
    if rt is None:
        raise NotImplementedError(
            'La generación de imágenes requiere un proveedor OpenAI habilitado '
            'con API key. Agregalo en /panel/ai/config/.'
        )
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError('SDK `openai` no instalado.') from exc

    client = OpenAI(api_key=rt.api_key)

    # Cuentas distintas tienen distinto modelo de imágenes disponible; probamos
    # del más nuevo al más compatible:
    #   - gpt-image-1: el más nuevo, pero requiere ORGANIZACIÓN VERIFICADA en OpenAI.
    #   - dall-e-3: acepta 1792x1024; no todas las cuentas lo tienen habilitado.
    #   - dall-e-2: disponible en casi todas las cuentas con crédito (fallback seguro).
    attempts = [
        {'model': 'gpt-image-1', 'size': '1536x1024', 'quality': 'medium'},
        {'model': 'dall-e-3', 'size': '1792x1024', 'quality': 'standard'},
        {'model': 'dall-e-2', 'size': '1024x1024'},
    ]
    last_exc = None
    for opts in attempts:
        try:
            resp = client.images.generate(prompt=prompt, n=1, **opts)
        except Exception as exc:  # noqa: BLE001 — probamos el siguiente modelo
            last_exc = exc
            continue
        item = resp.data[0]
        b64 = getattr(item, 'b64_json', None)
        if b64:
            return base64.b64decode(b64)
        url = getattr(item, 'url', None)
        if url:
            import urllib.request
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()

    # Si NINGÚN modelo de imagen funcionó, casi siempre es la key/cuenta de OpenAI:
    # sin acceso a imágenes, sin créditos, o key que no es de OpenAI.
    raise RuntimeError(
        'No se pudo generar la imagen. La cuenta de OpenAI configurada no tiene '
        'acceso a los modelos de imagen (gpt-image-1 requiere organización '
        'verificada; dall-e-3/2 requieren una API key real de OpenAI con crédito). '
        'Revisá la key del proveedor OpenAI en /panel/ai/config/. '
        f'Detalle técnico: {last_exc}'
    )


def _wrap_title(draw, text: str, font, max_width: int) -> list[str]:
    """Envuelve el título en líneas que quepan en max_width píxeles."""
    words = text.split()
    lines: list[str] = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:4]  # tope de 4 líneas


def compose_banner(bg_bytes: bytes, title: str) -> bytes:
    """Compone el fondo IA con el branding fijo y devuelve PNG en bytes."""
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    bg = Image.open(BytesIO(bg_bytes)).convert('RGBA')
    canvas = ImageOps.fit(bg, (CANVAS_W, CANVAS_H), Image.LANCZOS).convert('RGBA')

    # Degradado navy de izquierda→derecha para legibilidad del texto.
    overlay = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    fade_to = CANVAS_W * 0.72
    for x in range(CANVAS_W):
        a = int(235 * max(0.0, 1 - x / fade_to))
        odraw.line([(x, 0), (x, CANVAS_H)], fill=(*NAVY, a))
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    pad = 56

    # Logo UNEMI (arriba a la izquierda). El PNG es navy oscuro; lo recoloreamos a
    # BLANCO conservando su alpha, así se ve limpio y profesional sobre el fondo
    # oscuro SIN necesidad de un cuadro blanco detrás.
    try:
        logo = Image.open(LOGO_PATH).convert('RGBA')
        logo.thumbnail((230, 92), Image.LANCZOS)
        alpha = logo.split()[3]
        white_logo = Image.new('RGBA', logo.size, (255, 255, 255, 255))
        white_logo.putalpha(alpha)
        cx, cy = pad, 40
        canvas.alpha_composite(white_logo, (cx, cy))
        draw = ImageDraw.Draw(canvas)
        logo_bottom = cy + logo.height
    except FileNotFoundError:
        logo_bottom = 60

    # Mascota tigre (abajo a la derecha).
    try:
        tiger = Image.open(TIGER_PATH).convert('RGBA')
        tiger.thumbnail((250, 250), Image.LANCZOS)
        canvas.alpha_composite(tiger, (CANVAS_W - tiger.width - 24, CANVAS_H - tiger.height - 8))
    except FileNotFoundError:
        pass

    # Título del evento (grande, blanco, envuelto).
    title = (title or 'Evento UNEMI').strip()
    font_title = ImageFont.truetype(str(FONT_TITLE), 52)
    max_text_w = 700
    lines = _wrap_title(draw, title, font_title, max_text_w)
    line_h = font_title.getbbox('Ag')[3] + 16
    block_h = line_h * len(lines)
    y = max(logo_bottom + 48, (CANVAS_H - block_h) // 2)
    for line in lines:
        # Sombra suave para contraste.
        draw.text((pad + 2, y + 2), line, font=font_title, fill=(0, 0, 0, 160))
        draw.text((pad, y), line, font=font_title, fill=WHITE)
        y += line_h

    # Barra naranja + wordmark institucional debajo del título.
    draw.rectangle([pad, y + 8, pad + 64, y + 14], fill=ORANGE)
    font_body = ImageFont.truetype(str(FONT_BODY), 24)
    draw.text((pad, y + 24), 'UNEMI · Universidad Estatal de Milagro',
              font=font_body, fill=(226, 232, 240))

    # Wordmark de la app (certifAI) abajo a la izquierda — branding profesional.
    try:
        font_brand = ImageFont.truetype(str(FONT_TITLE), 26)
        bx, by = pad, CANVAS_H - 46
        draw.text((bx, by), 'certif', font=font_brand, fill=(255, 255, 255))
        wcertif = draw.textlength('certif', font=font_brand)
        draw.text((bx + wcertif, by), 'AI', font=font_brand, fill=ORANGE)
    except Exception:
        pass

    out = BytesIO()
    canvas.convert('RGB').save(out, format='PNG', optimize=True)
    return out.getvalue()


def _fallback_background(size=(CANVAS_W, CANVAS_H)) -> bytes:
    """Fondo branded generado LOCALMENTE (sin IA): degradado azul marca con un
    glow naranja. Se usa cuando la IA de imagen no está disponible (sin crédito
    de OpenAI, sin proveedor, etc.), para que el banner siempre se genere."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    W, H = size
    top = (28, 42, 99)   # navy un poco más claro arriba (#1c2a63)
    grad = Image.new('RGB', (1, H))
    for y in range(H):
        t = y / H
        grad.putpixel((0, y), tuple(int(top[i] + (NAVY[i] - top[i]) * t) for i in range(3)))
    base = grad.resize((W, H))

    # Glow naranja difuso (esquina superior derecha).
    glow = Image.new('RGB', (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gx, gy, gr = int(W * 0.80), int(H * 0.26), int(W * 0.28)
    gd.ellipse([gx - gr, gy - gr, gx + gr, gy + gr],
               fill=(int(ORANGE[0] * 0.55), int(ORANGE[1] * 0.42), int(ORANGE[2] * 0.30)))
    glow = glow.filter(ImageFilter.GaussianBlur(130))
    base = ImageChops.add(base, glow)

    out = BytesIO()
    base.save(out, format='PNG', optimize=True)
    return out.getvalue()


def generate_event_banner(title: str, custom_prompt: str = '') -> dict:
    """Genera el banner completo. Devuelve dict con base64 listo para el form.

    Si la IA de imagen no está disponible (sin crédito/proveedor), cae a un
    fondo branded local — el banner SIEMPRE se genera.

    {'implemented': True, 'image_base64': '<data:image/png;base64,...>',
     'prompt': '<prompt usado>', 'ai_background': bool, 'filename': 'banner-...png'}
    """
    prompt = build_prompt(title, custom_prompt)
    ai_background = True
    try:
        bg = _generate_background(prompt)
    except Exception as exc:  # noqa: BLE001 — sin IA usamos el fondo local
        import logging
        logging.getLogger(__name__).info('Banner sin IA (fondo local): %s', exc)
        bg = _fallback_background()
        ai_background = False
    png = compose_banner(bg, title)
    b64 = base64.b64encode(png).decode('ascii')
    slug = ''.join(c if c.isalnum() else '-' for c in (title or 'evento').lower())[:40].strip('-')
    return {
        'implemented': True,
        'image_base64': f'data:image/png;base64,{b64}',
        'prompt': prompt,
        'ai_background': ai_background,
        'filename': f'banner-ia-{slug or "evento"}.png',
    }
