"""Seed de catálogo completo (sin etiquetas 'Seed').

Genera, con nombres limpios y todo lleno:
  - Ponentes reales por cada seminario.
  - Seminarios sueltos: pasados (con evaluación) y FUTUROS hasta el 30/08/2026.
  - Un PROGRAMA abierto con seminarios futuros.
  - Evaluaciones (banco de preguntas) en cada seminario.
  - Para el participante Ronny: evaluaciones YA RENDIDAS (aprobadas) y
    evaluaciones ABIERTAS (pendientes de rendir), más inscripciones.
  - RESUMEN de IA (Betto) en absolutamente todos los seminarios.

Idempotente. Uso:
    python manage.py seed_catalogo
    python manage.py seed_catalogo --reset     # borra lo de este seed y recrea
"""
from datetime import date, time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import (
    Participant, Program, Event, Speaker, Enrollment, Attendance,
    Certificate, Signature, SessionSummary, ProcessingStatus,
)
from core.models.evaluations import (
    Evaluation, Question, EvaluationAttempt, QuestionKind, QuestionSource,
)
from core.services import programs as program_service

RONNY_EMAIL = 'ronnyareu22@gmail.com'


def q(kind, text, options, correct, expl):
    return dict(kind=kind, text=text, options=options, correct_idx=correct, explanation=expl)


def summary(md, points, steps, quiz):
    return dict(summary_md=md, key_points=points, next_steps=steps, quiz=quiz)


# ─────────────────────────── Seminarios sueltos ───────────────────────────
# ronny: 'passed' = asistió + evaluación aprobada + certificado
#        'open'   = asistió + evaluación activa SIN rendir (test abierto)
#        'enrolled' = inscrito (evento futuro), evaluación abierta
#        'none'   = disponible (Ronny no inscrito)
SEMINARS = [
    dict(
        title='Introducción a la Inteligencia Artificial',
        description='Panorama de la IA moderna: aprendizaje automático, redes neuronales y aplicaciones reales en la industria y la academia.',
        modality='virtual', virtual_platform='meet', location='',
        date=date(2026, 6, 10), start_time=time(18, 0), end_time=time(20, 0), hours=8,
        skills=['Conceptos de IA y aprendizaje automático', 'Tipos de modelos', 'Ética y sesgos en IA'],
        speaker=dict(name='Diego Ramírez', title='PhD.', affiliation='UNEMI',
                     bio='Investigador en inteligencia artificial y aprendizaje automático.'),
        ronny='passed',
        questions=[
            q('mcq', '¿Qué es el aprendizaje supervisado?',
              ['Aprender sin datos etiquetados', 'Aprender a partir de datos etiquetados', 'Aprender por refuerzo', 'Aprender sin modelo'],
              1, 'Usa datos con la respuesta correcta (etiqueta) para entrenar.'),
            q('boolean', 'Una red neuronal se inspira en el funcionamiento de las neuronas biológicas.',
              ['Verdadero', 'Falso'], 0, 'Las capas de neuronas artificiales procesan la información.'),
            q('mcq', '¿Cuál NO es una tarea típica de aprendizaje automático?',
              ['Clasificación', 'Regresión', 'Agrupamiento', 'Compilación'],
              3, 'Compilar código no es una tarea de ML.'),
            q('boolean', 'El sobreajuste (overfitting) ocurre cuando el modelo memoriza los datos de entrenamiento.',
              ['Verdadero', 'Falso'], 0, 'Rinde bien en entrenamiento pero mal en datos nuevos.'),
        ],
        summary=summary(
            'El seminario ofreció una **introducción a la inteligencia artificial**, distinguiendo el '
            '**aprendizaje supervisado** (datos etiquetados), **no supervisado** (agrupamiento) y por '
            '**refuerzo**. Se explicó qué es una **red neuronal** y los riesgos de **sobreajuste** y **sesgos**.',
            ['El aprendizaje supervisado usa datos etiquetados.',
             'Las redes neuronales se inspiran en las neuronas biológicas.',
             'El sobreajuste memoriza el entrenamiento y generaliza mal.',
             'La ética y los sesgos son claves en la IA responsable.'],
            ['Explorar un dataset y plantear un problema de clasificación.',
             'Entrenar un modelo simple y medir su exactitud.',
             'Revisar posibles sesgos en los datos.'],
            [{'type': 'mcq', 'question': '¿Qué usa el aprendizaje supervisado?',
              'options': ['Datos etiquetados', 'Ningún dato', 'Solo reglas', 'Solo imágenes'],
              'correct_idx': 0, 'explanation': 'Entrena con datos que incluyen la respuesta correcta.'}],
        ),
    ),
    dict(
        title='Desarrollo de APIs REST con FastAPI',
        description='Construcción de APIs modernas y veloces en Python con FastAPI: rutas, validación con Pydantic, documentación automática y asincronía.',
        modality='in_person', virtual_platform='', location='Laboratorio de Cómputo A — Edificio de Ingeniería',
        date=date(2026, 6, 27), start_time=time(15, 0), end_time=time(18, 0), hours=12,
        skills=['APIs REST con FastAPI', 'Validación con Pydantic', 'Programación asíncrona', 'Documentación OpenAPI'],
        speaker=dict(name='Carlos Mendoza', title='MSc.', affiliation='UNEMI',
                     bio='Ingeniero de software especializado en back-end y arquitecturas web.'),
        ronny='open',
        questions=[
            q('mcq', '¿Qué biblioteca usa FastAPI para validar datos?',
              ['Marshmallow', 'Pydantic', 'Cerberus', 'Voluptuous'], 1, 'Pydantic valida y tipa los datos de entrada/salida.'),
            q('boolean', 'FastAPI genera documentación interactiva (Swagger) de forma automática.',
              ['Verdadero', 'Falso'], 0, 'Expone /docs con la especificación OpenAPI.'),
            q('mcq', '¿Qué palabra clave define una función asíncrona en Python?',
              ['async', 'await', 'defer', 'thread'], 0, 'async def declara una corrutina.'),
            q('mcq', '¿Qué método HTTP se usa normalmente para crear un recurso?',
              ['GET', 'POST', 'DELETE', 'HEAD'], 1, 'POST crea recursos nuevos en el servidor.'),
        ],
        summary=summary(
            'Se construyeron **APIs REST con FastAPI**, aprovechando la **validación automática con Pydantic** '
            'y la **documentación OpenAPI** (Swagger) que el framework genera solo. Se trabajó la **asincronía** '
            'con `async`/`await` y los métodos HTTP para operaciones CRUD.',
            ['Pydantic valida y tipa los datos de la API.',
             'FastAPI genera la documentación Swagger automáticamente.',
             'async/await habilitan el manejo asíncrono de peticiones.',
             'POST crea recursos; GET los consulta.'],
            ['Crear un endpoint CRUD con FastAPI.',
             'Definir modelos de entrada/salida con Pydantic.',
             'Probar la API desde la documentación /docs.'],
            [{'type': 'boolean', 'question': 'FastAPI genera documentación Swagger automáticamente.',
              'options': ['Verdadero', 'Falso'], 'correct_idx': 0, 'explanation': 'Publica /docs con OpenAPI.'}],
        ),
    ),
    dict(
        title='Machine Learning con scikit-learn',
        description='Entrenamiento de modelos de aprendizaje automático en Python con scikit-learn: preparación de datos, entrenamiento, evaluación y ajuste.',
        modality='virtual', virtual_platform='meet', location='',
        date=date(2026, 8, 5), start_time=time(18, 0), end_time=time(21, 0), hours=16,
        skills=['Preparación de datos', 'Entrenamiento de modelos', 'Métricas de evaluación', 'Validación cruzada'],
        speaker=dict(name='Mónica Vera', title='MSc.', affiliation='UNEMI',
                     bio='Científica de datos y docente de aprendizaje automático.'),
        ronny='none',
        questions=[
            q('mcq', '¿Qué método de un modelo de scikit-learn lo entrena?',
              ['predict()', 'fit()', 'score()', 'transform()'], 1, 'fit() ajusta el modelo a los datos.'),
            q('boolean', 'La validación cruzada evalúa el modelo en varias particiones de los datos.',
              ['Verdadero', 'Falso'], 0, 'Reduce la dependencia de una sola división train/test.'),
            q('mcq', '¿Qué métrica mide el porcentaje de aciertos en clasificación?',
              ['MSE', 'Exactitud (accuracy)', 'R²', 'MAE'], 1, 'La exactitud es la proporción de predicciones correctas.'),
            q('mcq', '¿Por qué se separan datos de entrenamiento y de prueba?',
              ['Para acelerar', 'Para evaluar en datos no vistos', 'Por costumbre', 'Para ahorrar memoria'],
              1, 'Mide la capacidad de generalización del modelo.'),
        ],
        summary=summary(
            'El seminario cubrió el flujo de **machine learning con scikit-learn**: **preparación de datos**, '
            'entrenamiento con `fit()`, predicción con `predict()` y **evaluación** con métricas como la '
            '**exactitud**. Se explicó la **validación cruzada** y la separación train/test para medir la generalización.',
            ['fit() entrena el modelo; predict() genera predicciones.',
             'La validación cruzada evalúa en varias particiones.',
             'La exactitud mide el porcentaje de aciertos.',
             'Separar train/test evita evaluar sobre datos ya vistos.'],
            ['Entrenar un clasificador con un dataset propio.',
             'Medir la exactitud sobre el conjunto de prueba.',
             'Aplicar validación cruzada para comparar modelos.'],
            [{'type': 'mcq', 'question': '¿Qué método entrena un modelo en scikit-learn?',
              'options': ['fit()', 'predict()', 'plot()', 'open()'], 'correct_idx': 0,
              'explanation': 'fit() ajusta el modelo a los datos.'}],
        ),
    ),
    dict(
        title='Visualización de Datos con Power BI',
        description='Creación de tableros interactivos y reportes profesionales con Power BI para comunicar hallazgos y apoyar la toma de decisiones.',
        modality='virtual', virtual_platform='meet', location='',
        date=date(2026, 8, 19), start_time=time(18, 0), end_time=time(20, 30), hours=10,
        skills=['Modelado de datos en Power BI', 'Medidas con DAX', 'Diseño de dashboards', 'Storytelling con datos'],
        speaker=dict(name='Valeria Cedeño', title='Ing.', affiliation='UNEMI',
                     bio='Especialista en analítica de datos e inteligencia de negocios.'),
        ronny='enrolled',
        questions=[
            q('mcq', '¿Qué lenguaje se usa para crear medidas en Power BI?',
              ['SQL', 'DAX', 'Python', 'M'], 1, 'DAX (Data Analysis Expressions) crea medidas y columnas calculadas.'),
            q('boolean', 'Un buen dashboard prioriza la claridad sobre la cantidad de gráficos.',
              ['Verdadero', 'Falso'], 0, 'Menos ruido visual comunica mejor el mensaje.'),
            q('mcq', '¿Qué tipo de gráfico conviene para mostrar una evolución en el tiempo?',
              ['Circular (pastel)', 'De líneas', 'De dispersión', 'De árbol'], 1, 'El gráfico de líneas muestra tendencias temporales.'),
            q('boolean', 'El storytelling con datos busca guiar al lector hacia una conclusión clara.',
              ['Verdadero', 'Falso'], 0, 'Ordena los datos en una narrativa con propósito.'),
        ],
        summary=summary(
            'El seminario enseñó a construir **tableros con Power BI**: modelado de datos, creación de **medidas con DAX** '
            'y elección del **gráfico adecuado** (líneas para tendencias). Se enfatizó el **storytelling con datos**, '
            'priorizando la claridad para guiar al lector hacia una conclusión.',
            ['DAX crea medidas y columnas calculadas en Power BI.',
             'El gráfico de líneas comunica tendencias en el tiempo.',
             'Un buen dashboard prioriza la claridad.',
             'El storytelling ordena los datos en una narrativa.'],
            ['Modelar un conjunto de datos en Power BI.',
             'Crear medidas clave con DAX.',
             'Diseñar un dashboard con foco en el mensaje.'],
            [{'type': 'mcq', 'question': '¿Qué lenguaje crea medidas en Power BI?',
              'options': ['DAX', 'SQL', 'HTML', 'CSS'], 'correct_idx': 0, 'explanation': 'DAX define medidas y cálculos.'}],
        ),
    ),
    dict(
        title='Ciberseguridad para Desarrolladores Web',
        description='Buenas prácticas de seguridad en aplicaciones web: principales vulnerabilidades (OWASP), autenticación segura y protección de datos.',
        modality='in_person', virtual_platform='', location='Auditorio de la Facultad de Ingeniería',
        date=date(2026, 8, 28), start_time=time(15, 0), end_time=time(18, 0), hours=12,
        skills=['Vulnerabilidades OWASP', 'Autenticación y JWT', 'Protección contra inyecciones', 'Cifrado de datos'],
        speaker=dict(name='Andrea Solórzano', title='Ing.', affiliation='UNEMI',
                     bio='Desarrolladora y consultora en seguridad de aplicaciones web.'),
        ronny='none',
        questions=[
            q('mcq', '¿Qué ataque inyecta código SQL a través de la entrada del usuario?',
              ['XSS', 'Inyección SQL', 'CSRF', 'Phishing'], 1, 'La inyección SQL manipula consultas con entradas maliciosas.'),
            q('boolean', 'Las contraseñas deben guardarse cifradas (hasheadas), nunca en texto plano.',
              ['Verdadero', 'Falso'], 0, 'Se usan funciones de hash con sal para protegerlas.'),
            q('mcq', '¿Qué previene un token CSRF?',
              ['Robo de sesión por peticiones falsificadas', 'Inyección SQL', 'Fuerza bruta', 'Malware'],
              0, 'Valida que la petición provenga del sitio legítimo.'),
            q('mcq', '¿Qué estándar reúne las principales vulnerabilidades web?',
              ['ISO 9001', 'OWASP Top 10', 'RFC 2616', 'PEP 8'], 1, 'OWASP Top 10 lista los riesgos más críticos.'),
        ],
        summary=summary(
            'El seminario abordó la **seguridad en aplicaciones web** a partir del **OWASP Top 10**. Se explicaron ataques '
            'como la **inyección SQL**, **XSS** y **CSRF**, y las defensas: consultas parametrizadas, tokens CSRF, '
            'autenticación con **JWT** y almacenamiento de contraseñas **hasheadas** con sal.',
            ['La inyección SQL manipula consultas con entradas maliciosas.',
             'Las contraseñas se guardan hasheadas, nunca en texto plano.',
             'El token CSRF evita peticiones falsificadas.',
             'OWASP Top 10 reúne los riesgos web más críticos.'],
            ['Revisar el OWASP Top 10 en un proyecto propio.',
             'Parametrizar todas las consultas a la base de datos.',
             'Implementar autenticación con JWT y hashing de claves.'],
            [{'type': 'boolean', 'question': 'Las contraseñas deben guardarse en texto plano.',
              'options': ['Verdadero', 'Falso'], 'correct_idx': 1, 'explanation': 'Nunca: se guardan hasheadas con sal.'}],
        ),
    ),
]

# ─────────────────────────────── Programa abierto ──────────────────────────
PROGRAM = dict(
    name='Analítica de Negocios con Python',
    description=(
        'Programa orientado a convertir datos en decisiones: desde la manipulación de datos con '
        'Pandas y la construcción de modelos predictivos, hasta la comunicación de resultados '
        'mediante dashboards y storytelling.'
    ),
    body=(
        "Por haber completado satisfactoriamente el programa '{programa}', con un total de {horas} "
        "horas académicas y el desarrollo de las competencias en analítica de negocios detalladas."
    ),
    seminars=[
        dict(
            title='Fundamentos de Analítica y Pandas',
            description='Manipulación, limpieza y análisis exploratorio de datos con la librería Pandas de Python.',
            modality='virtual', virtual_platform='meet', location='',
            date=date(2026, 8, 8), start_time=time(18, 0), end_time=time(21, 0), hours=16,
            skills=['Estructuras de datos con Pandas', 'Limpieza de datos', 'Análisis exploratorio', 'Agregaciones'],
            speaker=dict(name='Mónica Vera', title='MSc.', affiliation='UNEMI',
                         bio='Científica de datos y docente de aprendizaje automático.'),
            questions=[
                q('mcq', '¿Qué estructura de Pandas representa una tabla bidimensional?',
                  ['Series', 'DataFrame', 'Array', 'Index'], 1, 'El DataFrame es la tabla de filas y columnas.'),
                q('boolean', 'dropna() elimina filas o columnas con valores faltantes.',
                  ['Verdadero', 'Falso'], 0, 'Sirve para limpiar datos incompletos.'),
                q('mcq', '¿Qué método agrupa datos para calcular agregados?',
                  ['merge()', 'groupby()', 'sort_values()', 'head()'], 1, 'groupby() agrupa y luego se agrega.'),
            ],
            summary=summary(
                'Se trabajó el **análisis de datos con Pandas**: el **DataFrame** como tabla principal, la **limpieza** '
                'con `dropna()` y el **análisis exploratorio** con `groupby()` para calcular agregados por categoría.',
                ['El DataFrame es la tabla central de Pandas.',
                 'dropna() elimina datos faltantes.',
                 'groupby() agrupa para calcular agregados.',
                 'El análisis exploratorio revela patrones iniciales.'],
                ['Cargar un CSV y explorar sus columnas.',
                 'Limpiar valores faltantes y duplicados.',
                 'Agrupar y resumir por categorías.'],
                [{'type': 'mcq', 'question': '¿Qué estructura de Pandas es una tabla 2D?',
                  'options': ['DataFrame', 'Series', 'Lista', 'Tupla'], 'correct_idx': 0,
                  'explanation': 'El DataFrame tiene filas y columnas.'}],
            ),
        ),
        dict(
            title='Modelado Predictivo con Python',
            description='Construcción y evaluación de modelos predictivos (regresión y clasificación) aplicados a problemas de negocio.',
            modality='virtual', virtual_platform='meet', location='',
            date=date(2026, 8, 15), start_time=time(18, 0), end_time=time(21, 0), hours=18,
            skills=['Regresión y clasificación', 'Selección de variables', 'Evaluación de modelos', 'Interpretación de resultados'],
            speaker=dict(name='Diego Ramírez', title='PhD.', affiliation='UNEMI',
                         bio='Investigador en inteligencia artificial y aprendizaje automático.'),
            questions=[
                q('mcq', '¿Qué modelo predice un valor numérico continuo?',
                  ['Clasificación', 'Regresión', 'Agrupamiento', 'Reducción'], 1, 'La regresión estima valores continuos.'),
                q('boolean', 'La matriz de confusión ayuda a evaluar un modelo de clasificación.',
                  ['Verdadero', 'Falso'], 0, 'Muestra aciertos y errores por clase.'),
                q('mcq', '¿Qué problema busca predecir una categoría (sí/no)?',
                  ['Regresión', 'Clasificación', 'Clustering', 'PCA'], 1, 'La clasificación asigna una etiqueta discreta.'),
            ],
            summary=summary(
                'El seminario cubrió el **modelado predictivo**: la **regresión** para valores continuos y la '
                '**clasificación** para categorías. Se evaluaron modelos con la **matriz de confusión** y se '
                'interpretaron los resultados en términos de negocio.',
                ['La regresión predice valores numéricos continuos.',
                 'La clasificación asigna categorías discretas.',
                 'La matriz de confusión evalúa la clasificación.',
                 'Interpretar el modelo conecta el resultado con el negocio.'],
                ['Plantear un problema de negocio como predicción.',
                 'Entrenar y evaluar un modelo de clasificación.',
                 'Interpretar los errores con la matriz de confusión.'],
                [{'type': 'mcq', 'question': '¿Qué modelo predice un valor continuo?',
                  'options': ['Regresión', 'Clasificación', 'Clustering', 'Ninguno'], 'correct_idx': 0,
                  'explanation': 'La regresión estima valores numéricos.'}],
            ),
        ),
        dict(
            title='Dashboards y Storytelling de Datos',
            description='Comunicación efectiva de resultados analíticos mediante tableros interactivos y narrativas basadas en datos.',
            modality='in_person', virtual_platform='', location='Sala de Innovación — Edificio de Ingeniería',
            date=date(2026, 8, 22), start_time=time(15, 0), end_time=time(18, 0), hours=12,
            skills=['Diseño de dashboards', 'Selección de gráficos', 'Storytelling con datos', 'Comunicación de hallazgos'],
            speaker=dict(name='Valeria Cedeño', title='Ing.', affiliation='UNEMI',
                         bio='Especialista en analítica de datos e inteligencia de negocios.'),
            questions=[
                q('mcq', '¿Qué gráfico conviene para comparar categorías?',
                  ['De líneas', 'De barras', 'De dispersión', 'De área'], 1, 'Las barras comparan magnitudes entre categorías.'),
                q('boolean', 'El storytelling con datos guía al público hacia una conclusión clara.',
                  ['Verdadero', 'Falso'], 0, 'Ordena la información con una narrativa e intención.'),
                q('mcq', '¿Qué se debe evitar en un buen dashboard?',
                  ['Claridad', 'Jerarquía visual', 'Exceso de gráficos', 'Consistencia'], 2, 'El exceso de gráficos genera ruido.'),
            ],
            summary=summary(
                'El seminario cerró el programa con la **comunicación de resultados**: elección del **gráfico adecuado** '
                '(barras para comparar categorías), **jerarquía visual** y **storytelling con datos** para guiar al '
                'público hacia una conclusión, evitando el exceso de gráficos.',
                ['Las barras comparan magnitudes entre categorías.',
                 'El storytelling guía hacia una conclusión clara.',
                 'El exceso de gráficos genera ruido visual.',
                 'La jerarquía visual ordena la atención del lector.'],
                ['Elegir el gráfico correcto para cada mensaje.',
                 'Construir un dashboard con jerarquía visual.',
                 'Narrar los hallazgos con una conclusión accionable.'],
                [{'type': 'mcq', 'question': '¿Qué gráfico compara categorías?',
                  'options': ['De barras', 'De líneas', 'De área', 'Pastel 3D'], 'correct_idx': 0,
                  'explanation': 'Las barras comparan magnitudes.'}],
            ),
        ),
    ],
)


class Command(BaseCommand):
    help = 'Seed de catálogo: ponentes, seminarios (pasados y futuros hasta 30/08), un programa abierto, evaluaciones abiertas y rendidas por Ronny, y resúmenes de IA en todo.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Borra lo de este seed y recrea.')

    def handle(self, *args, **options):
        if options['reset']:
            self._reset()

        with transaction.atomic():
            ronny = self._ronny()
            # Seminarios sueltos
            for cfg in SEMINARS:
                ev = self._ensure_event(cfg, program=None)
                self._ensure_speaker(ev, cfg['speaker'])
                evaluation = self._ensure_evaluation(ev, cfg['questions'])
                self._ensure_summary(ev, cfg['summary'])
                self._apply_ronny(ev, evaluation, ronny, cfg['ronny'])

            # Programa abierto (futuro) — Ronny inscrito, evaluaciones abiertas
            program = self._ensure_program(PROGRAM)
            for scfg in PROGRAM['seminars']:
                ev = self._ensure_event(scfg, program=program)
                self._ensure_speaker(ev, scfg['speaker'])
                self._ensure_evaluation(ev, scfg['questions'])
                self._ensure_summary(ev, scfg['summary'])
            program_service.get_or_create_program_batch(program)
            program_service.enroll_participant_in_program(program, ronny)

        self._report(ronny, program)

    # ── entidades ──────────────────────────────────────────────────────────
    def _ronny(self):
        p, _ = Participant.objects.get_or_create(
            email=RONNY_EMAIL,
            defaults=dict(national_id='0928374651', first_name='Ronny Isaac',
                          last_name='Arellano Urgiles', phone='0961234567'),
        )
        return p

    def _ensure_event(self, cfg, program):
        ev, _ = Event.objects.get_or_create(
            title=cfg['title'], date=cfg['date'],
            defaults=dict(
                description=cfg['description'], modality=cfg['modality'],
                virtual_platform=cfg['virtual_platform'], location=cfg['location'],
                start_time=cfg['start_time'], end_time=cfg['end_time'],
                hours=cfg['hours'], skills=cfg['skills'], program=program,
                is_active=True, quiz_enabled=True,
            ),
        )
        ev.description = cfg['description']; ev.modality = cfg['modality']
        ev.virtual_platform = cfg['virtual_platform']; ev.location = cfg['location']
        ev.start_time = cfg['start_time']; ev.end_time = cfg['end_time']
        ev.hours = cfg['hours']; ev.skills = cfg['skills']; ev.program = program
        ev.is_active = True; ev.quiz_enabled = True
        ev.save()
        self.stdout.write(f'  Seminario: {ev.title} ({ev.date}, {ev.hours} h)')
        return ev

    def _ensure_speaker(self, ev, sp):
        Speaker.objects.get_or_create(
            event=ev, name=sp['name'],
            defaults=dict(title=sp['title'], affiliation=sp['affiliation'], bio=sp['bio']),
        )

    def _ensure_evaluation(self, ev, questions):
        evaluation, _ = Evaluation.objects.get_or_create(
            event=ev,
            defaults=dict(title=f'Evaluación · {ev.title}',
                          description=f'Evalúa los aprendizajes del seminario «{ev.title}».',
                          pass_threshold=70, max_attempts=2, questions_per_attempt=0,
                          shuffle_questions=True, is_active=True),
        )
        evaluation.is_active = True
        evaluation.save(update_fields=['is_active'])
        for order, qq in enumerate(questions, start=1):
            Question.objects.get_or_create(
                evaluation=evaluation, text=qq['text'],
                defaults=dict(
                    kind=QuestionKind.MCQ if qq['kind'] == 'mcq' else QuestionKind.BOOLEAN,
                    options=qq['options'], correct_idx=qq['correct_idx'],
                    explanation=qq['explanation'], points=1,
                    source=QuestionSource.AI, order=order, is_active=True,
                ),
            )
        return evaluation

    def _ensure_summary(self, ev, s):
        summ, _ = SessionSummary.objects.get_or_create(event=ev)
        summ.status = ProcessingStatus.READY
        summ.summary_md = s['summary_md']
        summ.key_points = s['key_points']
        summ.next_steps = s['next_steps']
        summ.quiz = s.get('quiz', [])
        summ.transcript_raw = s['summary_md']
        summ.transcript_chars = len(s['summary_md'])
        summ.duration_minutes = (ev.hours or 0) * 60
        summ.ai_model = 'gpt-4o-mini'
        summ.processed_at = timezone.now()
        summ.save()

    def _ensure_program(self, cfg):
        program, _ = Program.objects.get_or_create(
            name=cfg['name'],
            defaults=dict(description=cfg['description'], faculty='FACI',
                          is_active=True, is_open=True, certificate_body=cfg['body']),
        )
        firmas = list(Signature.objects.filter(is_active=True).order_by('sort_order')[:3])
        for i, firma in enumerate(firmas, start=1):
            setattr(program, f'signature_inst_{i}', firma)
        program.description = cfg['description']; program.certificate_body = cfg['body']
        program.is_active = True; program.is_open = True
        program.save()
        self.stdout.write(f'  Programa: {program.name}')
        return program

    # ── relación con Ronny ─────────────────────────────────────────────────
    def _apply_ronny(self, ev, evaluation, ronny, mode):
        if mode == 'none':
            return
        Enrollment.objects.get_or_create(participant=ronny, event=ev, defaults={'confirmed': True})
        if mode in ('passed', 'open'):
            Attendance.objects.get_or_create(participant=ronny, event=ev)
        if mode == 'passed':
            self._pass_evaluation(evaluation, ronny)
            program_service.issue_seminar_certificate(ev, ronny)
        # 'open' y 'enrolled' quedan con la evaluación ABIERTA (sin intento)

    def _pass_evaluation(self, evaluation, ronny):
        best = evaluation.best_attempt_for(ronny)
        if best and best.passed:
            return
        preguntas = list(evaluation.active_questions)
        answers = {str(qq.id): qq.correct_idx for qq in preguntas}
        used = evaluation.attempts_used_by(ronny)
        EvaluationAttempt.objects.create(
            evaluation=evaluation, participant=ronny, attempt_number=used + 1,
            answers=answers, question_ids=[qq.id for qq in preguntas],
            correct=len(preguntas), total=len(preguntas),
            score=100.0, passed=True, submitted_at=timezone.now(),
        )

    # ── reset / report ─────────────────────────────────────────────────────
    def _reset(self):
        titles = [c['title'] for c in SEMINARS] + [s['title'] for s in PROGRAM['seminars']]
        for ev in Event.objects.filter(title__in=titles):
            if ev.batch_id:
                b = ev.batch
                b.certificates.all().delete()
                ev.batch = None; ev.save(update_fields=['batch'])
                b.delete()
            ev.delete()
        prog = Program.objects.filter(name=PROGRAM['name']).first()
        if prog:
            for b in prog.batches.all():
                b.certificates.all().delete(); b.delete()
            prog.delete()
        self.stdout.write(self.style.WARNING('Seed de catálogo previo eliminado.'))

    def _report(self, ronny, program):
        futuros = Event.objects.filter(date__gte=date(2026, 7, 18), date__lte=date(2026, 8, 30), is_active=True).count()
        certs = Certificate.objects.filter(national_id=ronny.national_id).count()
        self.stdout.write(self.style.SUCCESS(
            '\nSeed de catálogo listo:\n'
            f'  Seminarios sueltos : {len(SEMINARS)}\n'
            f'  Programa           : {program.name} ({program.course_count} seminarios)\n'
            f'  Eventos futuros (hasta 30/08): {futuros}\n'
            f'  Resúmenes IA       : en todos los seminarios\n'
            f'  Ronny — evaluación rendida (aprobada): «Introducción a la Inteligencia Artificial»\n'
            f'  Ronny — evaluaciones ABIERTAS: FastAPI + los 3 del programa + Power BI\n'
            f'  Ronny — certificados totales: {certs}'
        ))
