"""Registry de prompts de sistema editables por feature.

Cada feature tiene un prompt por defecto (canónico, aquí). El admin puede
sobreescribirlo desde /panel/ai/config/ (se guarda en `AIPrompt`). `get_prompt`
devuelve el override si existe y no está vacío, si no el default.

Para features cuyo formato de salida se parsea (resumen, cuestionario, banner),
el prompt editable es la parte de "persona/estilo"; las reglas estrictas de
formato JSON se agregan en código y no se editan (para no romper el parseo).
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


# ── Defaults por feature ──────────────────────────────────────────────

_EVENT_DESCRIPTION = """Sos un asistente experto en redacción de descripciones para eventos académicos y de capacitación profesional en español ecuatoriano.

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


_CERT_BODY = """Sos un redactor experto en textos de certificados académicos formales en español ecuatoriano.

REGLAS ESTRICTAS:
1. Devolvé SOLO TEXTO PLANO. NUNCA uses HTML, markdown, ni ninguna etiqueta.
2. Texto BREVE y conciso: entre 30 y 55 palabras, máximo 2 oraciones.
3. Es el cuerpo de un certificado oficial — formal, institucional, respetuoso.
4. Empezá con "Por haber completado satisfactoriamente..." / "En reconocimiento a..." / "Por su destacada participación en..." / "Por culminar con éxito...".
5. **OBLIGATORIO**: el texto DEBE incluir los placeholders literales `{curso}` y `{horas}` — se reemplazan al imprimir.
6. **TEMATIZACIÓN**: si el contexto incluye nombre del curso o facultad, reflejá 1-2 conceptos del dominio (salud, ingeniería, educación, etc.).
7. NO inventes instituciones, fechas ni datos que no estén en el contexto.
8. NO firmes, NO uses saludos ni emojis ni viñetas.
9. Tercera persona / impersonal."""


_SKILLS = (
    "Eres un diseñador instruccional. Dado un curso universitario, propones las "
    "competencias/habilidades concretas que un estudiante adquiere al completarlo. "
    "Respondes SOLO con un arreglo JSON de 3 a 6 strings cortos (máx. 8 palabras "
    "cada uno), en español, sin texto adicional ni ```."
)


_QUESTIONS = (
    "Eres un evaluador académico. A partir del material de un curso/programa, "
    "generas preguntas de evaluación que midan comprensión real (no trivias). "
    "Respondes SOLO con un arreglo JSON, sin texto adicional ni ```."
)


_SUMMARY = """Eres un asistente académico especializado en sintetizar \
clases, seminarios y conferencias universitarias para estudiantes.

Tu tarea: a partir de un transcript de Google Meet, generar un resumen \
estructurado en español para que un estudiante que no asistió pueda ponerse \
al día rápidamente."""


_BANNER = (
    'Estilo moderno, limpio y elegante, con colores institucionales azul '
    'marino oscuro (#162054) y acentos naranja (#F58830). Composición con '
    'amplio espacio negativo a la izquierda para colocar texto encima. '
    'Iluminación suave, alta calidad, sensación tecnológica y educativa.'
)


# key → (label, descripción, default). El orden define el orden en la UI.
REGISTRY: dict[str, dict] = {
    'summary': {
        'label': 'Resumen de sesión',
        'description': 'Persona del asistente que resume el transcript de Meet. Las reglas de formato JSON se añaden aparte.',
        'default': _SUMMARY,
    },
    'questions': {
        'label': 'Banco de preguntas (evaluación)',
        'description': 'Persona del evaluador que genera preguntas. El formato JSON de las preguntas se añade aparte.',
        'default': _QUESTIONS,
    },
    'skills': {
        'label': 'Sugerir habilidades',
        'description': 'Propone las competencias de un curso (devuelve arreglo JSON de strings).',
        'default': _SKILLS,
    },
    'event_description': {
        'label': 'Descripción de evento',
        'description': 'Copilot que redacta la descripción HTML de un evento.',
        'default': _EVENT_DESCRIPTION,
    },
    'cert_body': {
        'label': 'Cuerpo de certificado',
        'description': 'Redacta el texto del certificado (usa {curso} y {horas}).',
        'default': _CERT_BODY,
    },
    'banner': {
        'label': 'Banner con IA (estilo)',
        'description': 'Guía de estilo para el fondo del banner. El "sin texto/logos" se añade aparte.',
        'default': _BANNER,
    },
}


def default_prompt(key: str) -> str:
    entry = REGISTRY.get(key)
    return entry['default'] if entry else ''


def get_prompt(key: str) -> str:
    """Devuelve el prompt del feature: override de BD si hay, si no el default."""
    default = default_prompt(key)
    try:
        from core.models import AIPrompt
        row = AIPrompt.objects.filter(key=key).first()
        if row and (row.content or '').strip():
            return row.content
    except Exception:
        pass
    return default
