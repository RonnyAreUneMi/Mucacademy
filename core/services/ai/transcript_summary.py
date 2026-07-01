"""Pipeline IA: transcript de Meet → resumen ejecutivo + cuestionario.

Toma el texto plano del transcript y lo convierte en:
  - `resumen_md`: resumen ejecutivo en Markdown (3-5 párrafos).
  - `puntos_clave`: lista de bullets con los hallazgos más importantes.
  - `proximos_pasos`: acciones concretas recomendadas post-evento.
  - `cuestionario`: 5 preguntas opción múltiple para repasar lo aprendido.

Diseño:
  - Una sola llamada a Claude (con structured JSON output) para minimizar
    latencia y costo. Si la respuesta no es JSON parseable, se reintenta
    con un prompt más estricto (1 reintento).
  - El prompt está en español y orientado a contexto académico universitario.
  - Si el transcript es muy largo (>40k caracteres), se trunca a las primeras
    35k palabras (suficiente para una clase de 2h y cabe en la ventana del
    modelo Haiku 4.5).
"""
from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass, field

from .client import call_ai_full, get_runtime


log = logging.getLogger(__name__)


# Tope para no explotar la ventana del modelo. ~35k palabras ≈ ~50k tokens.
# Claude Haiku 4.5 maneja 200k de ventana, pero quemar tokens en transcripts
# crudos no aporta — los últimos 35k palabras de una sesión cubren todo el
# contenido relevante (las primeras suelen ser presentaciones).
MAX_TRANSCRIPT_WORDS = 35_000


_BASE_INTRO = """Eres un asistente académico especializado en sintetizar \
clases, seminarios y conferencias universitarias para estudiantes.

Tu tarea: a partir de un transcript de Google Meet, generar un resumen \
estructurado en español para que un estudiante que no asistió pueda ponerse \
al día rápidamente."""

_QUIZ_RULES = """
CUESTIONARIO — reglas obligatorias:
- Genera 5 preguntas que evalúen comprensión REAL del contenido (ideas, \
conceptos, relaciones), nunca detalles triviales como nombres propios o fechas.
- Mezcla tipos: al menos 2 preguntas de VERDADERO/FALSO ("type": "boolean") y \
el resto de opción múltiple ("type": "mcq").
- En las de opción múltiple, las 4 opciones deben ser plausibles y del mismo \
estilo/longitud (evita que la correcta se note por ser más larga o detallada).
- VARÍA la posición de la respuesta correcta entre A, B, C y D a lo largo del \
cuestionario. NO pongas la respuesta correcta siempre en la misma opción.
- Cada pregunta lleva una "explanation" breve que justifique la respuesta \
correcta (esto sirve como justificación pedagógica del quiz).

Formato de cada pregunta:
- Opción múltiple:
  {"type": "mcq", "question": "…", "options": ["…","…","…","…"], \
"correct_idx": 0, "explanation": "…"}   // options: exactamente 4, correct_idx 0-3
- Verdadero/Falso:
  {"type": "boolean", "question": "afirmación a evaluar", \
"options": ["Verdadero", "Falso"], "correct_idx": 0, "explanation": "…"}   // correct_idx 0 o 1"""

_JSON_SHAPE_WITH_QUIZ = """
El JSON debe tener exactamente esta forma:
{
  "resumen_md": "string en Markdown, 3-5 párrafos",
  "puntos_clave": ["string", ...],   // 5 a 8 items
  "proximos_pasos": ["string", ...], // 3 a 5 items
  "cuestionario": [ { pregunta }, ... ]   // 5 preguntas
}"""

_JSON_SHAPE_NO_QUIZ = """
El JSON debe tener exactamente esta forma:
{
  "resumen_md": "string en Markdown, 3-5 párrafos",
  "puntos_clave": ["string", ...],   // 5 a 8 items
  "proximos_pasos": ["string", ...], // 3 a 5 items
  "cuestionario": []                 // lista vacía (este evento no usa quiz)
}"""

_COMMON_RULES = """
REGLAS ESTRICTAS:
1. Tu respuesta DEBE ser un JSON válido, sin texto adicional ni cercas de \
código (sin ```json).
2. Usa lenguaje claro, accesible a estudiantes universitarios."""


def build_system_prompt(include_quiz: bool = True) -> str:
    """Arma el system prompt según si el evento usa cuestionario o no."""
    if include_quiz:
        return _BASE_INTRO + _COMMON_RULES + _JSON_SHAPE_WITH_QUIZ + _QUIZ_RULES
    return (
        _BASE_INTRO + _COMMON_RULES + _JSON_SHAPE_NO_QUIZ +
        '\nEste evento NO requiere cuestionario: deja "cuestionario" como lista vacía.'
    )


# Compat: prompt por defecto (con quiz).
SYSTEM_PROMPT = build_system_prompt(True)


USER_TEMPLATE = """Sesión: {titulo}
Fecha: {fecha}
Duración estimada: {duracion} minutos

--- TRANSCRIPT ---
{transcript}
--- FIN TRANSCRIPT ---

Genera el resumen en JSON según el formato especificado."""


@dataclass(slots=True)
class SummaryResult:
    """Resultado del pipeline IA."""
    resumen_md: str = ''
    puntos_clave: list[str] = field(default_factory=list)
    proximos_pasos: list[str] = field(default_factory=list)
    cuestionario: list[dict] = field(default_factory=list)
    duracion_minutos: int = 0
    ai_model: str = ''
    ai_input_tokens: int = 0
    ai_output_tokens: int = 0


def _truncate(text: str) -> str:
    """Trunca a MAX_TRANSCRIPT_WORDS conservando el principio y el final."""
    words = text.split()
    if len(words) <= MAX_TRANSCRIPT_WORDS:
        return text
    half = MAX_TRANSCRIPT_WORDS // 2
    head = ' '.join(words[:half])
    tail = ' '.join(words[-half:])
    return f'{head}\n\n[... fragmento intermedio omitido por longitud ...]\n\n{tail}'


def _strip_code_fences(s: str) -> str:
    """Si el modelo devolvió ```json ... ```, quitamos las cercas."""
    s = s.strip()
    if s.startswith('```'):
        # primer salto de línea descarta "```json" o "```"
        first_nl = s.find('\n')
        if first_nl != -1:
            s = s[first_nl + 1:]
        if s.endswith('```'):
            s = s[:-3]
    return s.strip()


def _parse_json_strict(raw: str) -> dict:
    """Parsea el JSON. Si falla, intenta extraer el primer objeto {} balanceado."""
    cleaned = _strip_code_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Fallback: buscar el primer objeto JSON balanceado
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f'No se pudo parsear JSON. Inicio: {cleaned[:200]}')


def _validate_summary(data: dict) -> None:
    """Valida la forma del JSON. Lanza ValueError si no cumple."""
    required = ('resumen_md', 'puntos_clave', 'proximos_pasos', 'cuestionario')
    for k in required:
        if k not in data:
            raise ValueError(f'Falta campo obligatorio: {k}')
    if not isinstance(data['cuestionario'], list):
        raise ValueError('cuestionario debe ser lista')
    for i, q in enumerate(data['cuestionario']):
        if not isinstance(q, dict):
            raise ValueError(f'Pregunta #{i} no es objeto')
        for f in ('question', 'options', 'correct_idx'):
            if f not in q:
                raise ValueError(f'Pregunta #{i} no tiene {f}')
        # Acepta opción múltiple (4) o verdadero/falso (2).
        if not isinstance(q['options'], list) or len(q['options']) not in (2, 4):
            raise ValueError(f'Pregunta #{i} debe tener 2 (V/F) o 4 opciones')
        if not isinstance(q['correct_idx'], int) or not 0 <= q['correct_idx'] < len(q['options']):
            raise ValueError(f'Pregunta #{i} tiene correct_idx fuera de rango')


def _shuffle_quiz(cuestionario: list) -> list:
    """Baraja las opciones de cada pregunta y recalcula correct_idx.

    Elimina cualquier sesgo posicional del modelo (p.ej. respuesta siempre en B).
    Las V/F (2 opciones) se dejan como 'Verdadero'/'Falso' en orden fijo pero
    con su correct_idx correcto; solo se barajan las de opción múltiple.
    """
    for q in cuestionario:
        opts = q.get('options') or []
        ci = q.get('correct_idx', 0)
        if len(opts) == 2:
            # Normaliza V/F al orden estándar Verdadero/Falso.
            q.setdefault('type', 'boolean')
            continue
        if len(opts) != 4 or not (0 <= ci < 4):
            continue
        pairs = list(enumerate(opts))          # (idx_original, texto)
        random.shuffle(pairs)
        q['options'] = [t for _, t in pairs]
        q['correct_idx'] = next(new for new, (orig, _) in enumerate(pairs) if orig == ci)
        q.setdefault('type', 'mcq')
    return cuestionario


def summarize_transcript(
    transcript: str,
    *,
    titulo: str = '',
    fecha: str = '',
    duracion_minutos: int = 0,
    include_quiz: bool = True,
) -> SummaryResult:
    """Llama al modelo IA configurado y devuelve el resumen estructurado.

    Lanza:
      - NotImplementedError si IA no está configurada (sin api_key, etc.).
      - ValueError si la respuesta no se pudo parsear tras 1 reintento.
      - RuntimeError si el SDK del proveedor falta.
    """
    rt = get_runtime()
    if rt is None:
        raise NotImplementedError(
            'IA no configurada. Andá a /panel/ai/config/ para activarla.'
        )

    truncated = _truncate(transcript)
    system_prompt = build_system_prompt(include_quiz)
    user_msg = USER_TEMPLATE.format(
        titulo=titulo or '(sin título)',
        fecha=fecha or '(no especificada)',
        duracion=duracion_minutos or 0,
        transcript=truncated,
    )

    resp = call_ai_full(rt, system_prompt, user_msg)
    total_in = resp.input_tokens
    total_out = resp.output_tokens
    log.info('IA respondió %d chars (modelo=%s, in=%d, out=%d)',
             len(resp.text), rt.model, total_in, total_out)

    try:
        data = _parse_json_strict(resp.text)
        _validate_summary(data)
    except (ValueError, json.JSONDecodeError) as e:
        log.warning('Primer intento JSON inválido (%s). Reintentando…', e)
        # Reintento con prompt más enfático
        retry_system = system_prompt + (
            '\n\nIMPORTANTE: Tu intento anterior no fue JSON válido. '
            'Esta vez devuelve EXCLUSIVAMENTE el objeto JSON, sin texto antes '
            'ni después, sin ```.'
        )
        resp = call_ai_full(rt, retry_system, user_msg)
        total_in += resp.input_tokens
        total_out += resp.output_tokens
        data = _parse_json_strict(resp.text)
        _validate_summary(data)

    # Sin quiz → aseguramos lista vacía; con quiz → barajamos para evitar sesgo.
    cuestionario = list(data.get('cuestionario') or [])
    if include_quiz:
        cuestionario = _shuffle_quiz(cuestionario)
    else:
        cuestionario = []

    return SummaryResult(
        resumen_md=data['resumen_md'],
        puntos_clave=list(data.get('puntos_clave', [])),
        proximos_pasos=list(data.get('proximos_pasos', [])),
        cuestionario=cuestionario,
        duracion_minutos=duracion_minutos,
        ai_model=rt.model,
        ai_input_tokens=total_in,
        ai_output_tokens=total_out,
    )
