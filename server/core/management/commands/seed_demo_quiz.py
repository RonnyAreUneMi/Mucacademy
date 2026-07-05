"""
Seed de demostración del flujo de evaluación (quiz) y certificado.

Crea 2 eventos presentables (títulos reales, sin marcas de "seed"):
  A) "Fundamentos de Inteligencia Artificial en la Educación"
     → REQUIERE aprobar el quiz (nota mínima 70%) para el certificado.
  B) "Conversatorio: Ética y Tecnología en la Universidad"
     → NO usa quiz (charla informativa, certificado por asistencia).

Ambos con resumen IA READY; el A con un cuestionario mixto (opción múltiple
+ verdadero/falso, respuestas en distintas posiciones). Inscribe y marca
asistencia de un participante demo para poder recorrer el flujo completo.

Idempotente (get_or_create por título + fecha). Uso:
    python manage.py seed_demo_quiz
    python manage.py seed_demo_quiz --reset   # borra y recrea
"""
from datetime import date, time

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    Event, SessionSummary, ProcessingStatus,
    Participant, Enrollment, Attendance,
)

DEMO_DATE = date(2026, 6, 25)

QUIZ = [
    {
        "type": "mcq",
        "question": "¿Cuál es el rol principal de la IA en la educación según la sesión?",
        "options": [
            "Reemplazar por completo a los docentes",
            "Potenciar al docente y personalizar el aprendizaje",
            "Eliminar las evaluaciones",
            "Reducir el acceso al conocimiento",
        ],
        "correct_idx": 1,
        "explanation": "La IA potencia al docente y permite personalizar el aprendizaje, no lo reemplaza.",
    },
    {
        "type": "boolean",
        "question": "La validación humana del contenido generado por IA sigue siendo indispensable.",
        "options": ["Verdadero", "Falso"],
        "correct_idx": 0,
        "explanation": "El docente debe revisar y contrastar el material generado por IA.",
    },
    {
        "type": "mcq",
        "question": "¿Qué permite la evaluación adaptativa con IA?",
        "options": [
            "Ajustar la dificultad según las respuestas del estudiante",
            "Solo calificar al final del curso",
            "Evitar toda retroalimentación",
            "Impedir segundos intentos",
        ],
        "correct_idx": 0,
        "explanation": "La evaluación adaptativa ajusta la dificultad y da retroalimentación inmediata.",
    },
    {
        "type": "mcq",
        "question": "¿Cuál de estos es un eje de accesibilidad mencionado?",
        "options": [
            "Encarecer el material",
            "Limitar los idiomas",
            "Transcripción automática y lectura de texto",
            "Prohibir el uso de dispositivos",
        ],
        "correct_idx": 2,
        "explanation": "La IA habilita transcripción, traducción y lectura para mayor accesibilidad.",
    },
    {
        "type": "boolean",
        "question": "Se recomienda proteger la privacidad de los datos de los estudiantes al usar IA.",
        "options": ["Verdadero", "Falso"],
        "correct_idx": 0,
        "explanation": "La protección de datos es una de las recomendaciones clave de la sesión.",
    },
]

SUMMARY_A = (
    "En esta sesión se abordaron los **fundamentos de la inteligencia artificial "
    "aplicada a la educación**. Se destacó que la IA no reemplaza al docente, sino "
    "que lo potencia: automatiza tareas repetitivas y permite personalizar el "
    "aprendizaje según el desempeño de cada estudiante.\n\n"
    "Se revisaron tres ejes: **personalización**, **evaluación adaptativa** y "
    "**accesibilidad**. También se enfatizó la importancia de la validación humana "
    "del contenido generado y la protección de datos de los estudiantes."
)

SUMMARY_B = (
    "Conversatorio sobre **ética y tecnología** en el ámbito universitario. Se "
    "discutieron los dilemas del uso responsable de herramientas digitales, la "
    "privacidad y el pensamiento crítico frente a la información. Fue una charla "
    "de sensibilización, sin evaluación asociada."
)


class Command(BaseCommand):
    help = "Crea 2 eventos demo del flujo de quiz/certificado (uno exige quiz, otro no)."

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Borra y recrea los eventos demo.')

    def handle(self, *args, **options):
        titulo_a = 'Fundamentos de Inteligencia Artificial en la Educación'
        titulo_b = 'Conversatorio: Ética y Tecnología en la Universidad'

        if options['reset']:
            Event.objects.filter(title__in=[titulo_a, titulo_b], date=DEMO_DATE).delete()
            self.stdout.write(self.style.WARNING('Eventos demo previos eliminados.'))

        # ── Evento A: requiere quiz ──────────────────────────────
        ev_a, _ = Event.objects.get_or_create(
            title=titulo_a, date=DEMO_DATE,
            defaults=dict(
                description='Sesión introductoria sobre IA aplicada a la enseñanza.',
                modality='virtual', virtual_platform='meet',
                start_time=time(9, 0), end_time=time(11, 0),
                quiz_enabled=True, certificate_requires_quiz=True, quiz_pass_threshold=70,
            ),
        )
        ev_a.quiz_enabled = True
        ev_a.certificate_requires_quiz = True
        ev_a.quiz_pass_threshold = 70
        ev_a.save(update_fields=['quiz_enabled', 'certificate_requires_quiz', 'quiz_pass_threshold'])

        sa, _ = SessionSummary.objects.get_or_create(event=ev_a)
        sa.status = ProcessingStatus.READY
        sa.summary_md = SUMMARY_A
        sa.key_points = [
            'La IA potencia al docente, no lo reemplaza.',
            'Personalización del aprendizaje según el desempeño.',
            'Evaluación adaptativa con retroalimentación inmediata.',
            'Accesibilidad: transcripción, traducción y lectura de texto.',
            'Validación humana y protección de datos son indispensables.',
        ]
        sa.next_steps = [
            'Capacitar a docentes en uso ético de IA.',
            'Definir políticas de privacidad de datos.',
            'Pilotear una herramienta de tutoría inteligente.',
        ]
        sa.quiz = QUIZ
        sa.transcript_raw = SUMMARY_A
        sa.transcript_chars = len(SUMMARY_A)
        sa.duration_minutes = 120
        sa.ai_model = 'demo-seed'
        sa.processed_at = timezone.now()
        sa.save()

        # ── Evento B: sin quiz ───────────────────────────────────
        ev_b, _ = Event.objects.get_or_create(
            title=titulo_b, date=DEMO_DATE,
            defaults=dict(
                description='Charla de sensibilización sobre ética y tecnología.',
                modality='in_person', location='Auditorio Principal — Edificio A',
                start_time=time(15, 0), end_time=time(16, 30),
                quiz_enabled=False, certificate_requires_quiz=False,
            ),
        )
        ev_b.quiz_enabled = False
        ev_b.certificate_requires_quiz = False
        ev_b.save(update_fields=['quiz_enabled', 'certificate_requires_quiz'])

        sb, _ = SessionSummary.objects.get_or_create(event=ev_b)
        sb.status = ProcessingStatus.READY
        sb.summary_md = SUMMARY_B
        sb.key_points = [
            'Uso responsable de la tecnología en la universidad.',
            'Privacidad y pensamiento crítico frente a la información.',
        ]
        sb.next_steps = ['Fomentar espacios de debate sobre ética digital.']
        sb.quiz = []
        sb.transcript_raw = SUMMARY_B
        sb.transcript_chars = len(SUMMARY_B)
        sb.duration_minutes = 90
        sb.ai_model = 'demo-seed'
        sb.processed_at = timezone.now()
        sb.save()

        # ── Participante demo con inscripción + asistencia ───────
        participante, _ = Participant.objects.get_or_create(
            email='demo.participante@unemi.edu.ec',
            defaults=dict(national_id='0000000001', first_name='María', last_name='Demo'),
        )
        for ev in (ev_a, ev_b):
            Enrollment.objects.get_or_create(participant=participante, event=ev, defaults={'confirmed': True})
            Attendance.objects.get_or_create(participant=participante, event=ev)

        self.stdout.write(self.style.SUCCESS(
            'Seed demo listo:\n'
            f'  • {titulo_a}\n'
            f'      → requiere quiz (min {ev_a.quiz_pass_threshold}%), {len(QUIZ)} preguntas.\n'
            f'  • {titulo_b}\n'
            f'      → sin quiz (certificado por asistencia).\n'
            f'  Participante demo: {participante.email} (inscrito + asistió a ambos).'
        ))
