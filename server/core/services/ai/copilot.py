"""Copilot IA para descripciones de eventos.

Genera HTML enriquecido a partir del título del evento + un prompt libre
del usuario + una acción (crear / mejorar / expandir / resumir / formal /
amigable). El HTML que devuelve es compatible con CKEditor (etiquetas
limitadas: p, strong, em, ul, ol, li, h2, h3, blockquote, br).
"""
from __future__ import annotations

from .client import call_ai, is_configured


SYSTEM_PROMPT = """Sos un asistente experto en redacción de descripciones para eventos académicos y de capacitación profesional en español ecuatoriano.

REGLAS ESTRICTAS:
1. Devolvé SOLO HTML válido, sin explicaciones ni markdown. Empezá directo con la primera etiqueta.
2. Etiquetas permitidas: <p>, <strong>, <em>, <ul>, <ol>, <li>, <h2>, <h3>, <blockquote>, <br>.
3. NO uses <html>, <body>, <head>, <div>, <span>, <script>, <style> ni atributos.
4. Tono profesional pero cercano. Sin jerga corporativa vacía.
5. **Usá ESTRUCTURA visual real** (no solo <p>):
   - Primer <p>: párrafo de bienvenida con la propuesta de valor.
   - <h2>¿Qué aprenderás?</h2> seguido de <ul><li>...</li></ul> con 3-5 bullets concretos.
   - <h2>¿A quién va dirigido?</h2> seguido de <p> describiendo el público.
   - <p> de cierre con call-to-action suave (ej.: "Te esperamos para...").
6. Resaltá conceptos clave dentro de los párrafos con <strong>.
7. Entre 100 y 250 palabras (salvo que la acción pida resumir → 1-2 párrafos cortos sin estructura).
8. Sin emojis. Sin firmas. Sin saludos al final.
9. Respetá el español ecuatoriano (usá "ustedes", no "vosotros").
10. Si el contexto del usuario es vago, asumí lo mínimo razonable y no inventes datos específicos (fechas, nombres de ponentes, lugares concretos).

Si no podés generar algo coherente, devolvé un párrafo simple."""


ACTION_INSTRUCTIONS = {
    'create':   'Generá una descripción NUEVA desde cero usando el título y el contexto.',
    'improve':  'MEJORÁ la descripción actual: redacción, claridad, estructura. No agregues información que no esté.',
    'expand':   'EXPANDÍ la descripción actual con más detalle, ejemplos y estructura. Mantené el sentido original.',
    'shorten':  'RESUMÍ la descripción actual a 1-2 párrafos cortos, sin perder lo esencial.',
    'formal':   'Reescribí en un tono FORMAL e institucional, manteniendo la información.',
    'friendly': 'Reescribí en un tono más AMIGABLE y cercano, sin perder profesionalismo.',
}


def improve_event_description(
    titulo: str,
    accion: str = 'create',
    contexto: str = '',
    descripcion_actual: str = '',
) -> dict:
    """Genera HTML para la descripción de un evento.

    Devuelve `{'implemented': bool, 'html'?: str, 'message'?: str}`.
    """
    titulo = (titulo or '').strip()
    if not titulo:
        return {'implemented': False, 'message': 'Necesitamos al menos el título del evento.'}

    if not is_configured():
        return {
            'implemented': False,
            'message': 'IA no configurada. Andá a Admin → Configuración IA y activá un proveedor.',
        }

    action_key = accion if accion in ACTION_INSTRUCTIONS else 'create'
    action_instr = ACTION_INSTRUCTIONS[action_key]

    parts = [
        f'TÍTULO DEL EVENTO: {titulo}',
        f'ACCIÓN: {action_instr}',
    ]
    if contexto.strip():
        parts.append(f'CONTEXTO ADICIONAL DEL ORGANIZADOR:\n{contexto.strip()}')
    if descripcion_actual.strip() and action_key in ('improve', 'expand', 'shorten', 'formal', 'friendly'):
        parts.append(f'DESCRIPCIÓN ACTUAL (para refinar):\n{descripcion_actual.strip()}')

    user_message = '\n\n'.join(parts) + '\n\nDevolvé solo el HTML.'

    try:
        from .prompts import get_prompt
        html = call_ai(system=get_prompt('event_description'), user=user_message)
    except NotImplementedError as exc:
        return {'implemented': False, 'message': str(exc)}
    except Exception as exc:  # noqa: BLE001 — devolvemos el error al admin
        return {'implemented': False, 'message': f'{type(exc).__name__}: {exc}'}

    return {'implemented': True, 'html': _sanitize_html(html), 'action': action_key}


def _sanitize_html(html: str) -> str:
    """Limpieza ligera: quita backticks o ```html que a veces el modelo devuelve."""
    text = (html or '').strip()
    # Si empieza con ```html ... ``` lo limpiamos
    if text.startswith('```'):
        text = text.lstrip('`').lstrip()
        if text.lower().startswith('html'):
            text = text[4:].lstrip()
        if text.endswith('```'):
            text = text[:-3].rstrip()
    return text.strip()


# ── Compat con código viejo (Fase 8 placeholder) ─────────────

CERT_BODY_SYSTEM = """Sos un redactor experto en textos de certificados académicos formales en español ecuatoriano.

REGLAS ESTRICTAS:
1. Devolvé SOLO TEXTO PLANO. NUNCA uses HTML, markdown, ni ninguna etiqueta (<p>, <strong>, <h2>, **, etc.).
2. Texto BREVE y conciso: entre 30 y 55 palabras, máximo 2 oraciones.
3. Es el cuerpo de un certificado oficial — formal, institucional, respetuoso.
4. Empezá con "Por haber completado satisfactoriamente..." / "En reconocimiento a..." / "Por su destacada participación en..." / "Por culminar con éxito...".
5. **OBLIGATORIO**: el texto DEBE incluir los placeholders literales `{curso}` y `{horas}` — se reemplazan al imprimir.
   - NO escribas "el seminario" suelto: usá `{curso}`.
   - NO escribas "40 horas" o cualquier cantidad: usá `{horas}`.

6. **TEMATIZACIÓN OBLIGATORIA**: si el contexto incluye nombre del curso o facultad, ANALIZÁ el dominio temático y reflejalo con 1-2 conceptos relevantes:
   - Salud / médico → "habilidades clínicas", "práctica sanitaria", "atención al paciente", "competencias en salud comunitaria"
   - Ingeniería / tecnología → "competencias técnicas", "innovación tecnológica", "resolución de problemas de ingeniería"
   - Educación / docencia → "prácticas pedagógicas", "didáctica", "competencias educativas"
   - Ciencias sociales → "investigación social", "desarrollo comunitario", "análisis crítico"
   - Posgrado / investigación → "rigor académico", "producción científica"
   - Gestión / administración → "liderazgo", "gestión estratégica", "toma de decisiones"
   - Si no podés inferir tema → usá "su formación profesional" como fallback genérico.

   El texto NO debe sonar igual para todos los certificados. Si el curso es "Salud Pública 2026", debe mencionar salud. Si es "Programación Avanzada", debe mencionar tecnología/programación.

7. NO inventes nombres de instituciones, fechas, ni datos que no estén en el contexto.
8. NO firmes, NO uses saludos ni emojis ni viñetas.
9. Tercera persona / impersonal (no "ustedes", no "tú").

EJEMPLOS DE RESPUESTA CORRECTA según tema:
- Curso "Salud Comunitaria": "Por haber completado satisfactoriamente el {curso}, con una duración de {horas} horas, fortaleciendo competencias en atención sanitaria y desarrollo de prácticas en salud comunitaria con compromiso institucional."
- Curso "IA en Educación": "Por culminar con éxito el {curso}, completando {horas} horas de formación en didáctica e innovación pedagógica aplicada a entornos digitales con dedicación académica."
- Curso "Programación Web": "En reconocimiento a su destacada participación en el {curso}, donde durante {horas} horas desarrolló competencias técnicas en desarrollo de software con rigor profesional."
- Sin contexto temático: "Por haber completado satisfactoriamente el {curso} de {horas} horas, demostrando compromiso, responsabilidad y excelencia en su formación profesional."

EJEMPLOS INCORRECTOS:
❌ "Por completar el seminario..." — falta {curso}
❌ "...con 40 horas..." — falta {horas}
❌ Usar el mismo texto genérico para "Salud" y "Programación" — TEMATIZÁ
❌ HTML o markdown"""


CERT_BODY_ACTIONS = {
    'create':  'Generá un cuerpo de certificado nuevo desde cero.',
    'rewrite': 'Reescribí el texto actual mejorando la redacción y formalidad. Mantené la idea base.',
    'shorten': 'Acortá el texto actual a 1 oración breve.',
    'expand':  'Expandí ligeramente el texto actual a 2 oraciones, sin perder formalidad.',
}


def generate_body_text(
    tipo_evento: str = 'seminario',
    contexto: str = '',
    tono: str = 'formal',
    accion: str = 'create',
) -> dict:
    """Genera el cuerpo (texto plano) de un certificado académico.

    Distinto de `improve_event_description` (que devuelve HTML para CKEditor):
    aquí queremos texto plano breve para imprimir directo en el PDF.
    """
    if not is_configured():
        return {
            'implemented': False,
            'message': 'IA no configurada. Andá a Admin → Configuración IA.',
        }

    action_key = accion if accion in CERT_BODY_ACTIONS else 'create'
    parts = [
        f'TIPO DE EVENTO: {tipo_evento}',
        f'TONO: {tono}',
        f'ACCIÓN: {CERT_BODY_ACTIONS[action_key]}',
    ]
    if contexto.strip():
        parts.append(f'TEXTO ACTUAL O CONTEXTO:\n{contexto.strip()[:500]}')

    user_message = '\n\n'.join(parts) + '\n\nDevolvé sólo el texto plano del cuerpo del certificado.'

    try:
        from .prompts import get_prompt
        text = call_ai(system=get_prompt('cert_body'), user=user_message)
    except NotImplementedError as exc:
        return {'implemented': False, 'message': str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {'implemented': False, 'message': f'{type(exc).__name__}: {exc}'}

    # Limpieza extra: quita HTML/markdown si el modelo se equivocó
    cleaned = _strip_html_and_markdown(text)
    # Defensivo: si el modelo ignoró la regla y no incluyó los placeholders,
    # los inyectamos sustituyendo menciones genéricas por las variables.
    cleaned = _ensure_placeholders(cleaned)
    return {'implemented': True, 'text': cleaned, 'action': action_key}


def _ensure_placeholders(text: str) -> str:
    """Garantiza que el texto contenga {curso} y {horas} aunque el LLM los omitiera.

    Estrategia:
    - Si ya contiene `{curso}` y `{horas}` → no toca nada.
    - Si falta `{curso}`: reemplaza la primera ocurrencia de "el seminario|el curso|
      el taller|la capacitación|la conferencia|el evento" por "el {curso}".
    - Si falta `{horas}`: agrega ", con una duración de {horas} horas" antes del
      primer punto si no encuentra mención de horas.
    """
    import re
    if not text:
        return text

    has_curso = '{curso}' in text
    has_horas = '{horas}' in text

    if not has_curso:
        # Substituye términos genéricos por {curso}
        pattern = re.compile(
            r'\b(el seminario|el curso|el taller|la capacitaci[óo]n|la conferencia|el evento)\b',
            re.IGNORECASE,
        )
        new_text, n = pattern.subn('el {curso}', text, count=1)
        if n > 0:
            text = new_text
            has_curso = True

    if not has_horas:
        # Si menciona "X horas" con número, lo reemplazamos por {horas} horas
        text_with_var, n = re.subn(r'\b\d+\s*horas?\b', '{horas} horas', text, count=1)
        if n > 0:
            text = text_with_var
            has_horas = True

    # Si todavía faltan los placeholders, los agregamos al final con un fallback
    if not has_curso or not has_horas:
        # Quita el punto final si lo tiene
        cleaned = text.rstrip('.').rstrip()
        appendix = []
        if not has_curso:
            appendix.append('en el {curso}')
        if not has_horas:
            appendix.append('con una duración de {horas} horas')
        text = cleaned + ', ' + ' '.join(appendix) + '.'

    return text


def _strip_html_and_markdown(s: str) -> str:
    """Saca tags HTML, asteriscos de markdown, comillas envolventes y trim."""
    import re
    if not s:
        return ''
    # Quita backticks de bloque ```...```
    s = s.strip()
    if s.startswith('```'):
        s = s.lstrip('`').lstrip()
        if s.endswith('```'):
            s = s[:-3].rstrip()
    # Quita tags HTML
    s = re.sub(r'<[^>]+>', '', s)
    # Quita markdown bold/italic
    s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
    s = re.sub(r'\*(.+?)\*', r'\1', s)
    s = re.sub(r'__(.+?)__', r'\1', s)
    # Comprime espacios y saltos múltiples
    s = re.sub(r'\s+', ' ', s)
    # Quita comillas envolventes que el modelo a veces agrega
    s = s.strip().strip('"\'').strip()
    return s
