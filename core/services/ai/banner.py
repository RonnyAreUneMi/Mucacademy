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

from .client import get_runtime

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
    """Arma el prompt para la IA. Siempre fuerza estilo UNEMI y SIN texto."""
    tema = custom.strip() or title.strip()
    return (
        'Fondo abstracto y profesional para el banner de un evento académico '
        f"universitario. Tema visual: {tema}. "
        'Estilo moderno, limpio y elegante, con colores institucionales azul '
        'marino oscuro (#162054) y acentos naranja (#F58830). Composición con '
        'amplio espacio negativo a la izquierda para colocar texto encima. '
        'Iluminación suave, alta calidad, sensación tecnológica y educativa. '
        'MUY IMPORTANTE: sin ningún texto, sin letras, sin palabras, sin logos, '
        'sin marcas de agua, sin personas mirando a cámara.'
    )


def _generate_background(prompt: str) -> bytes:
    """Llama a OpenAI DALL·E y devuelve los bytes PNG del fondo.

    Lanza NotImplementedError si no hay IA configurada o el proveedor no
    soporta imágenes (solo OpenAI).
    """
    rt = get_runtime()
    if rt is None:
        raise NotImplementedError(
            'IA no configurada. Andá a /panel/ai/config/ y elegí OpenAI + API key.'
        )
    if rt.provider != 'openai':
        raise NotImplementedError(
            f'La generación de imágenes requiere proveedor OpenAI '
            f'(actual: {rt.provider}). Cambialo en /panel/ai/config/.'
        )
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError('SDK `openai` no instalado.') from exc

    client = OpenAI(api_key=rt.api_key)

    # Cuentas distintas tienen distinto modelo de imágenes disponible.
    # gpt-image-1 (nuevo) devuelve siempre b64; dall-e-3 (anterior) acepta size 1792.
    attempts = [
        {'model': 'gpt-image-1', 'size': '1536x1024', 'quality': 'medium'},
        {'model': 'dall-e-3', 'size': '1792x1024', 'quality': 'standard'},
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
    raise RuntimeError(f'No se pudo generar la imagen: {last_exc}')


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

    # Logo UNEMI (arriba a la izquierda). El logo es navy oscuro, así que se
    # coloca sobre un "chip" blanco redondeado para que sea legible en el fondo
    # oscuro (si no, se pierde por contraste navy-sobre-navy).
    try:
        logo = Image.open(LOGO_PATH).convert('RGBA')
        logo.thumbnail((230, 92), Image.LANCZOS)
        cx, cy, cpad = pad, 40, 16
        chip = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        ImageDraw.Draw(chip).rounded_rectangle(
            [cx - cpad, cy - cpad, cx + logo.width + cpad, cy + logo.height + cpad],
            radius=18, fill=(255, 255, 255, 240),
        )
        canvas = Image.alpha_composite(canvas, chip)
        canvas.alpha_composite(logo, (cx, cy))
        draw = ImageDraw.Draw(canvas)  # recrear el draw tras el composite
        logo_bottom = cy + logo.height + cpad
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

    out = BytesIO()
    canvas.convert('RGB').save(out, format='PNG', optimize=True)
    return out.getvalue()


def generate_event_banner(title: str, custom_prompt: str = '') -> dict:
    """Genera el banner completo. Devuelve dict con base64 listo para el form.

    {'implemented': True, 'image_base64': '<data:image/png;base64,...>',
     'prompt': '<prompt usado>', 'filename': 'banner-...png'}
    """
    prompt = build_prompt(title, custom_prompt)
    bg = _generate_background(prompt)
    png = compose_banner(bg, title)
    b64 = base64.b64encode(png).decode('ascii')
    slug = ''.join(c if c.isalnum() else '-' for c in (title or 'evento').lower())[:40].strip('-')
    return {
        'implemented': True,
        'image_base64': f'data:image/png;base64,{b64}',
        'prompt': prompt,
        'filename': f'banner-ia-{slug or "evento"}.png',
    }
