"""Seed completo de demostración para un participante real.

Crea, para el participante **Ronny Isaac Arellano Urgiles**:
  - Un PROGRAMA ("Desarrollo Web Full-Stack") con 3 seminarios reales, cada uno
    con horas, competencias, ponente, descripción y todo lleno.
  - Un BANCO DE PREGUNTAS (evaluación formal) por seminario, con 5 preguntas
    mixtas (opción múltiple + V/F), con explicación.
  - Inscripción + asistencia a los 3 seminarios.
  - Un INTENTO APROBADO (100%) en la evaluación de cada seminario.
  - El CERTIFICADO de cada seminario y el CERTIFICADO DEL PROGRAMA, todos
    asociados al participante (aparecen en "mis certificados").

Idempotente: re-ejecutar no duplica. Uso:
    python manage.py seed_ronny_programa
    python manage.py seed_ronny_programa --reset       # borra y recrea
    python manage.py seed_ronny_programa --password Xyz # fija clave de acceso
"""
from datetime import date, time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import (
    Participant, Program, Event, Speaker, Enrollment, Attendance,
    CertificateBatch, Certificate, Signature,
)
from core.models.evaluations import (
    Evaluation, Question, EvaluationAttempt, QuestionKind, QuestionSource,
)
from core.services import programs as program_service


# ─────────────────────────── Datos del participante ───────────────────────────
PART = dict(
    national_id='0954187381',
    first_name='Ronny Isaac',
    last_name='Arellano Urgiles',
    email='ronnyareu22@gmail.com',
    phone='0961234567',
)
DEFAULT_PASSWORD = 'CertifAI2026'

# ─────────────────────────────── Datos del programa ───────────────────────────
PROGRAM_NAME = 'Desarrollo Web Full-Stack'
PROGRAM_DESC = (
    'Programa integral que forma al participante en el desarrollo de aplicaciones '
    'web modernas de extremo a extremo: desde la maquetación e interactividad en el '
    'navegador, pasando por la construcción de servicios en el servidor, hasta la '
    'gestión de datos y el despliegue en la nube.'
)
PROGRAM_BODY = (
    "Por haber culminado satisfactoriamente el programa '{programa}', completando "
    "la totalidad de sus seminarios con un total de {horas} horas académicas y "
    "desarrollando las competencias profesionales detalladas a continuación."
)

# Cada seminario, con TODO lleno.
SEMINARS = [
    dict(
        title='Fundamentos de HTML, CSS y JavaScript',
        description=(
            'Bases de la construcción de interfaces web: estructura semántica con '
            'HTML5, estilos y maquetación responsiva con CSS3 e interactividad con '
            'JavaScript moderno (ES6).'
        ),
        modality='virtual', virtual_platform='meet', meeting_url='',
        location='',
        date=date(2026, 5, 5), start_time=time(18, 0), end_time=time(21, 0),
        hours=20,
        skills=[
            'Maquetación HTML5 semántica',
            'Estilos con CSS3 y Flexbox',
            'Programación con JavaScript ES6',
            'Diseño web responsivo',
        ],
        speaker=dict(
            name='Andrea Solórzano', title='Ing.', affiliation='UNEMI',
            bio='Desarrolladora front-end y docente de tecnologías web.',
        ),
        evaluation=dict(
            title='Evaluación · Fundamentos de HTML, CSS y JavaScript',
            description='Evalúa los conceptos base de maquetación, estilos e interactividad.',
            questions=[
                dict(kind='mcq',
                     text='¿Qué etiqueta HTML5 representa el contenido principal de una página?',
                     options=['<div>', '<main>', '<section>', '<content>'], correct_idx=1,
                     explanation='<main> identifica el contenido principal y único del documento.'),
                dict(kind='boolean',
                     text='Flexbox permite alinear y distribuir elementos en una dimensión (fila o columna).',
                     options=['Verdadero', 'Falso'], correct_idx=0,
                     explanation='Flexbox es un modelo de caja unidimensional.'),
                dict(kind='mcq',
                     text='¿Cuál palabra clave declara una variable de bloque en JavaScript ES6?',
                     options=['var', 'let', 'function', 'define'], correct_idx=1,
                     explanation='let (y const) tienen alcance de bloque, a diferencia de var.'),
                dict(kind='mcq',
                     text='¿Qué unidad CSS es relativa al tamaño de fuente del elemento raíz?',
                     options=['px', 'em', 'rem', 'pt'], correct_idx=2,
                     explanation='rem se calcula respecto al font-size del elemento raíz (html).'),
                dict(kind='boolean',
                     text='El atributo "alt" en una imagen mejora la accesibilidad y el SEO.',
                     options=['Verdadero', 'Falso'], correct_idx=0,
                     explanation='Describe la imagen para lectores de pantalla y buscadores.'),
            ],
        ),
    ),
    dict(
        title='Backend con Python y Django',
        description=(
            'Construcción de la lógica del servidor y APIs con Python y el framework '
            'Django: modelos, vistas, ORM y servicios REST con Django REST Framework.'
        ),
        modality='in_person', virtual_platform='', meeting_url='',
        location='Laboratorio de Cómputo B — Edificio de Ingeniería',
        date=date(2026, 5, 19), start_time=time(18, 0), end_time=time(21, 0),
        hours=30,
        skills=[
            'Programación orientada a objetos en Python',
            'Framework Django (MVT)',
            'APIs REST con Django REST Framework',
            'Modelado de datos con el ORM',
        ],
        speaker=dict(
            name='Carlos Mendoza', title='MSc.', affiliation='UNEMI',
            bio='Ingeniero de software especializado en back-end y arquitecturas web.',
        ),
        evaluation=dict(
            title='Evaluación · Backend con Python y Django',
            description='Evalúa la construcción de servicios y APIs con Django.',
            questions=[
                dict(kind='mcq',
                     text='En Django, ¿qué componente define la estructura de los datos?',
                     options=['La vista', 'El modelo', 'La plantilla', 'La URL'], correct_idx=1,
                     explanation='El modelo mapea las tablas de la base de datos.'),
                dict(kind='boolean',
                     text='El ORM de Django permite consultar la base de datos sin escribir SQL directamente.',
                     options=['Verdadero', 'Falso'], correct_idx=0,
                     explanation='El ORM traduce operaciones de Python a SQL.'),
                dict(kind='mcq',
                     text='¿Qué comando aplica los cambios de modelos a la base de datos?',
                     options=['runserver', 'makemigrations', 'migrate', 'collectstatic'], correct_idx=2,
                     explanation='migrate ejecuta las migraciones pendientes sobre la base.'),
                dict(kind='mcq',
                     text='¿Qué biblioteca se usa para construir APIs REST en Django?',
                     options=['Flask', 'Django REST Framework', 'FastAPI', 'Jinja'], correct_idx=1,
                     explanation='DRF es la biblioteca estándar para APIs REST en Django.'),
                dict(kind='boolean',
                     text='Un serializer en DRF convierte objetos del modelo a JSON y viceversa.',
                     options=['Verdadero', 'Falso'], correct_idx=0,
                     explanation='Serializa y valida datos entre el modelo y la API.'),
            ],
        ),
    ),
    dict(
        title='Bases de Datos y Despliegue en la Nube',
        description=(
            'Diseño y consulta de bases de datos relacionales, y publicación de la '
            'aplicación en producción usando contenedores e integración continua.'
        ),
        modality='virtual', virtual_platform='meet', meeting_url='',
        location='',
        date=date(2026, 6, 2), start_time=time(18, 0), end_time=time(21, 0),
        hours=25,
        skills=[
            'Modelado de bases de datos relacionales',
            'Consultas SQL con PostgreSQL',
            'Contenedores con Docker',
            'Despliegue e integración continua (CI/CD)',
        ],
        speaker=dict(
            name='Valeria Cedeño', title='Ing.', affiliation='UNEMI',
            bio='Especialista en datos e infraestructura de despliegue en la nube.',
        ),
        evaluation=dict(
            title='Evaluación · Bases de Datos y Despliegue en la Nube',
            description='Evalúa el modelado de datos, SQL y el despliegue en producción.',
            questions=[
                dict(kind='mcq',
                     text='¿Qué cláusula SQL filtra las filas de una consulta?',
                     options=['ORDER BY', 'WHERE', 'GROUP BY', 'JOIN'], correct_idx=1,
                     explanation='WHERE aplica condiciones para seleccionar filas.'),
                dict(kind='boolean',
                     text='Una llave foránea (foreign key) relaciona una tabla con otra.',
                     options=['Verdadero', 'Falso'], correct_idx=0,
                     explanation='Referencia la clave primaria de la tabla relacionada.'),
                dict(kind='mcq',
                     text='¿Qué es Docker?',
                     options=[
                         'Un lenguaje de programación',
                         'Una plataforma de contenedores',
                         'Un motor de base de datos',
                         'Un editor de código',
                     ], correct_idx=1,
                     explanation='Docker empaqueta la app y sus dependencias en contenedores.'),
                dict(kind='mcq',
                     text='¿Qué significa CI/CD?',
                     options=[
                         'Código Interno / Código Distribuido',
                         'Integración Continua / Despliegue Continuo',
                         'Control de Índices / Control de Datos',
                         'Consulta Indexada / Consulta Directa',
                     ], correct_idx=1,
                     explanation='Automatiza la integración y el despliegue del software.'),
                dict(kind='boolean',
                     text='PostgreSQL es un sistema de gestión de bases de datos relacional.',
                     options=['Verdadero', 'Falso'], correct_idx=0,
                     explanation='Es un RDBMS de código abierto ampliamente usado.'),
            ],
        ),
    ),
]


class Command(BaseCommand):
    help = 'Seed completo: programa con 3 seminarios, banco de preguntas, evaluaciones aprobadas y certificados para Ronny Isaac.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Borra y recrea todo el seed.')
        parser.add_argument('--password', default=DEFAULT_PASSWORD, help='Clave de acceso del participante.')
        parser.add_argument('--email', default=PART['email'], help='Email del participante a usar.')

    # ───────────────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        email = options['email']
        password = options['password']

        if options['reset']:
            self._reset(email)

        with transaction.atomic():
            participante = self._ensure_participant(email, password)
            program = self._ensure_program()
            seminarios = self._ensure_seminars(program)

            # Diseño del programa (crea el lote de programa + logo UNEMI).
            program_service.get_or_create_program_batch(program)

            # Inscripción a todos los seminarios del programa.
            program_service.enroll_participant_in_program(program, participante)

            for ev, cfg in seminarios:
                self._mark_attendance(ev, participante)
                evaluation = self._ensure_evaluation(ev, cfg['evaluation'])
                self._pass_evaluation(evaluation, participante)
                self._issue_seminar_certificate(ev, participante, program)

            # Certificado del programa (idempotente).
            program_cert, _ = program_service.issue_program_certificate(program, participante)

        self._report(participante, program, password)

    # ───────────────────────────────────────────────────────────────────
    def _ensure_participant(self, email, password):
        p, created = Participant.objects.get_or_create(
            email=email,
            defaults=dict(
                national_id=PART['national_id'],
                first_name=PART['first_name'],
                last_name=PART['last_name'],
                phone=PART['phone'],
            ),
        )
        # Rellena campos faltantes sin pisar datos existentes válidos.
        changed = False
        if not p.national_id:
            p.national_id = PART['national_id']; changed = True
        if not p.first_name:
            p.first_name = PART['first_name']; changed = True
        if not p.last_name:
            p.last_name = PART['last_name']; changed = True
        if not p.phone:
            p.phone = PART['phone']; changed = True
        # Asegura acceso: fija la clave (es su propia cuenta demo).
        p.set_password(password); changed = True
        if changed:
            p.save()
        self.stdout.write(f'  Participante: {p.full_name} <{p.email}> (cédula {p.national_id})')
        return p

    def _ensure_program(self):
        program, _ = Program.objects.get_or_create(
            name=PROGRAM_NAME,
            defaults=dict(
                description=PROGRAM_DESC,
                faculty='FACI',
                is_active=True,
                is_open=True,
                certificate_body=PROGRAM_BODY,
            ),
        )
        # Firmas del programa (usa las institucionales activas si existen).
        firmas = list(Signature.objects.filter(is_active=True).order_by('sort_order')[:3])
        for i, firma in enumerate(firmas, start=1):
            setattr(program, f'signature_inst_{i}', firma)
        program.description = program.description or PROGRAM_DESC
        program.certificate_body = program.certificate_body or PROGRAM_BODY
        program.is_active = True
        program.is_open = True
        program.save()
        self.stdout.write(f'  Programa: {program.name}')
        return program

    def _ensure_seminars(self, program):
        seminarios = []
        for cfg in SEMINARS:
            ev, _ = Event.objects.get_or_create(
                title=cfg['title'], date=cfg['date'],
                defaults=dict(
                    description=cfg['description'],
                    modality=cfg['modality'],
                    virtual_platform=cfg['virtual_platform'],
                    meeting_url=cfg['meeting_url'],
                    location=cfg['location'],
                    start_time=cfg['start_time'], end_time=cfg['end_time'],
                    hours=cfg['hours'], skills=cfg['skills'],
                    program=program,
                    is_active=True,
                    quiz_enabled=True,
                ),
            )
            # Asegura vínculo y datos aunque ya existiera.
            ev.program = program
            ev.description = cfg['description']
            ev.modality = cfg['modality']
            ev.virtual_platform = cfg['virtual_platform']
            ev.location = cfg['location']
            ev.start_time = cfg['start_time']
            ev.end_time = cfg['end_time']
            ev.hours = cfg['hours']
            ev.skills = cfg['skills']
            ev.is_active = True
            ev.save()

            sp = cfg['speaker']
            Speaker.objects.get_or_create(
                event=ev, name=sp['name'],
                defaults=dict(title=sp['title'], affiliation=sp['affiliation'], bio=sp['bio']),
            )
            seminarios.append((ev, cfg))
            self.stdout.write(f'    Seminario: {ev.title} ({ev.hours} h, {len(ev.skills)} competencias)')
        return seminarios

    def _mark_attendance(self, ev, participante):
        Enrollment.objects.get_or_create(
            participant=participante, event=ev, defaults={'confirmed': True},
        )
        Attendance.objects.get_or_create(participant=participante, event=ev)

    def _ensure_evaluation(self, ev, cfg):
        evaluation, _ = Evaluation.objects.get_or_create(
            event=ev,
            defaults=dict(
                title=cfg['title'], description=cfg['description'],
                pass_threshold=70, max_attempts=2,
                questions_per_attempt=0, shuffle_questions=True, is_active=True,
            ),
        )
        evaluation.is_active = True
        evaluation.save(update_fields=['is_active'])
        # Banco de preguntas (idempotente por texto).
        for order, q in enumerate(cfg['questions'], start=1):
            Question.objects.get_or_create(
                evaluation=evaluation, text=q['text'],
                defaults=dict(
                    kind=QuestionKind.MCQ if q['kind'] == 'mcq' else QuestionKind.BOOLEAN,
                    options=q['options'], correct_idx=q['correct_idx'],
                    explanation=q['explanation'], points=1,
                    source=QuestionSource.AI, order=order, is_active=True,
                ),
            )
        self.stdout.write(f'      Evaluación: {evaluation.question_count} preguntas')
        return evaluation

    def _pass_evaluation(self, evaluation, participante):
        """Crea (si no existe) un intento APROBADO al 100%."""
        best = evaluation.best_attempt_for(participante)
        if best and best.passed:
            return best
        preguntas = list(evaluation.active_questions)
        answers = {str(q.id): q.correct_idx for q in preguntas}
        qids = [q.id for q in preguntas]
        used = evaluation.attempts_used_by(participante)
        attempt = EvaluationAttempt.objects.create(
            evaluation=evaluation, participant=participante,
            attempt_number=used + 1,
            answers=answers, question_ids=qids,
            correct=len(preguntas), total=len(preguntas),
            score=100.0, passed=True, submitted_at=timezone.now(),
        )
        return attempt

    def _issue_seminar_certificate(self, ev, participante, program):
        lote = ev.batch
        if lote is None:
            lote = CertificateBatch.objects.create(name=ev.title, faculty=program.faculty)
            applied = program_service.apply_program_design(program, lote)
            if not applied:
                firmas = list(Signature.objects.filter(is_active=True).order_by('sort_order')[:3])
                for i, firma in enumerate(firmas, start=1):
                    setattr(lote, f'signature_inst_{i}', firma)
                lote.save()
            ev.batch = lote
            ev.save(update_fields=['batch'])

        Certificate.objects.get_or_create(
            batch=lote, participant=participante,
            defaults=dict(
                national_id=participante.national_id,
                first_name=participante.first_name,
                last_name=participante.last_name,
                email=participante.email,
                phone=participante.phone,
                course=(ev.title or lote.name).upper(),
                course_date=ev.date,
                hours=ev.hours or 0,
            ),
        )

    # ───────────────────────────────────────────────────────────────────
    def _reset(self, email):
        program = Program.objects.filter(name=PROGRAM_NAME).first()
        if program:
            # Certificado + lote del programa.
            for batch in program.batches.all():
                batch.certificates.all().delete()
                batch.delete()
            # Seminarios: su lote + certificados + evaluación (cascada).
            for course in list(program.courses.all()):
                if course.batch_id:
                    b = course.batch
                    b.certificates.all().delete()
                    course.batch = None
                    course.save(update_fields=['batch'])
                    b.delete()
                course.delete()   # cascada: evaluación, preguntas, intentos, asistencias
            program.delete()
        self.stdout.write(self.style.WARNING('Seed previo eliminado.'))

    def _report(self, participante, program, password):
        certs = Certificate.objects.filter(participant=participante).count()
        self.stdout.write(self.style.SUCCESS(
            '\nSeed completo listo:\n'
            f'  Participante : {participante.full_name} <{participante.email}>\n'
            f'  Cédula       : {participante.national_id}\n'
            f'  Clave acceso : {password}\n'
            f'  Programa     : {program.name} ({program.course_count} seminarios, {program.total_hours} h)\n'
            f'  Certificados : {certs} en total (1 de programa + {program.course_count} de seminario)\n'
            f'  Evaluaciones : aprobadas al 100% en cada seminario.'
        ))
