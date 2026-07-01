"""Seed de datos demo COMPLETO para CertifAI (esquema en inglés).

Crea: participantes, lote + certificados, eventos (pasados/futuros,
virtual/presencial), inscripciones, asistencias, y un evento finalizado con
su SessionSummary (resumen IA + cuestionario) para que las pantallas de
Betto muestren datos.

Uso:
    python manage.py shell < scripts/seed_full_demo.py
"""
from datetime import date, time, timedelta

from django.utils import timezone

from core.models import (
    Participant, CertificateBatch, Certificate, Event, Speaker,
    Enrollment, Attendance, SessionSummary, ProcessingStatus, User,
)

today = date.today()

# ── Participante demo (login) ─────────────────────────────────────
demo, _ = Participant.objects.get_or_create(
    email="test@unemi.edu.ec",
    defaults={"first_name": "Ronny", "last_name": "Arellano", "national_id": "0928374651", "phone": "0998452317"},
)
demo.set_password("demo12345")
demo.is_leader = True
demo.save()

# Otros participantes
otros = []
for i, (fn, ln, nid) in enumerate([
    ("María", "González", "0912345678"),
    ("Carlos", "Vera", "0923456789"),
    ("Ana", "Mendoza", "0934567890"),
]):
    p, _ = Participant.objects.get_or_create(
        email=f"part{i}@unemi.edu.ec",
        defaults={"first_name": fn, "last_name": ln, "national_id": nid},
    )
    otros.append(p)

# ── Lote + certificados ───────────────────────────────────────────
admin = User.objects.filter(is_superuser=True).first()
batch, _ = CertificateBatch.objects.get_or_create(
    name="Capacitación Continua 2026 · FACI",
    defaults={"faculty": "FACI", "administrator": admin, "is_active": True},
)
for p in [demo] + otros:
    Certificate.objects.get_or_create(
        batch=batch, participant=p, verification_hash=f"DEMO{p.id:04d}HASH",
        defaults={
            "national_id": p.national_id or "", "first_name": p.first_name,
            "last_name": p.last_name, "email": p.email,
            "course": "Curso de Capacitación Continua en IA aplicada",
            "course_date": today - timedelta(days=20), "hours": 40,
        },
    )

# ── Eventos ───────────────────────────────────────────────────────
def mk_event(title, days_offset, virtual, location="", desc=""):
    ev, _ = Event.objects.get_or_create(
        title=title,
        defaults={
            "description": desc or "Evento académico organizado por UNEMI.",
            "modality": "virtual" if virtual else "in_person",
            "virtual_platform": "meet" if virtual else "",
            "meeting_url": "https://meet.google.com/abc-defg-hij" if virtual else "",
            "location": location,
            "date": today + timedelta(days=days_offset),
            "start_time": time(18, 0) if virtual else time(9, 0),
            "end_time": time(20, 0) if virtual else time(12, 0),
            "capacity": 120, "is_active": True, "batch": batch,
            "transcription_enabled": virtual,
        },
    )
    return ev

ev_pasado = mk_event("Webinar · Claude Code + Figma para Desarrollo", -3, True,
                     desc="Cómo acelerar el desarrollo con IA: de modelos Django a interfaces móviles.")
ev_proximo = mk_event("Webinar · Tendencias de IA en Educación", 3, True,
                      desc="Sesión virtual con expertos en aplicaciones de IA en aulas universitarias.")
ev_taller = mk_event("Talleres de Diseño UX", 10, False, location="Auditorio FACS · Bloque B")
ev_congreso = mk_event("Congreso de Innovación Docente UNEMI", 18, False, location="Auditorio Central · Milagro")

# Ponentes
Speaker.objects.get_or_create(event=ev_pasado, name="Ronny Arellano",
    defaults={"title": "Ing.", "affiliation": "UNEMI", "bio": "Desarrollador full-stack."})
Speaker.objects.get_or_create(event=ev_proximo, name="Dra. Laura Cedeño",
    defaults={"title": "PhD", "affiliation": "UNEMI", "bio": "Investigadora en EdTech."})

# ── Inscripciones + asistencia del demo ───────────────────────────
Enrollment.objects.get_or_create(participant=demo, event=ev_pasado, defaults={"confirmed": True})
Enrollment.objects.get_or_create(participant=demo, event=ev_proximo, defaults={"confirmed": True})
Enrollment.objects.get_or_create(participant=demo, event=ev_taller, defaults={"confirmed": True})
for p in otros:
    Enrollment.objects.get_or_create(participant=p, event=ev_pasado, defaults={"confirmed": True})
# El demo asistió al taller (presencial)
Attendance.objects.get_or_create(participant=demo, event=ev_taller)

# ── Evento finalizado CON resumen IA + cuestionario ───────────────
summary, _ = SessionSummary.objects.get_or_create(event=ev_pasado)
summary.status = ProcessingStatus.READY
summary.drive_file_id = "demo-drive-file-id"
summary.drive_file_name = "Webinar Claude Code + Figma - 2026 - Transcript"
summary.transcript_chars = 1100
summary.duration_minutes = 45
summary.ai_model = "gpt-4o-mini"
summary.ai_input_tokens = 600
summary.ai_output_tokens = 720
summary.processed_at = timezone.now()
summary.summary_md = (
    "La sesión exploró cómo **Claude Code** acelera el desarrollo de aplicaciones, "
    "desde la generación de modelos Django hasta interfaces móviles con React Native.\n\n"
    "Se demostró el flujo **diseño → código** usando Figma como fuente de verdad visual, "
    "y cómo los agentes de IA traducen mockups en componentes funcionales manteniendo el sistema de diseño.\n\n"
    "El expositor enfatizó la importancia de un **contrato de API consistente** y la "
    "refactorización progresiva como prácticas clave para proyectos escalables."
)
summary.key_points = [
    "Claude Code genera modelos y migraciones Django manteniendo convenciones del proyecto.",
    "Figma actúa como source-of-truth: los tokens de diseño se traducen a CSS variables.",
    "Los agentes paralelos permiten refactorizar decenas de archivos manteniendo consistencia.",
    "El efecto liquid glass se logra con BlurView en iOS y overlays translúcidos en Android.",
    "Un contrato de API en inglés bien documentado reduce errores entre backend y mobile.",
]
summary.next_steps = [
    "Definir el sistema de diseño en Figma antes de codear pantallas nuevas.",
    "Documentar el contrato de API para que mobile y web consuman las mismas claves.",
    "Usar ramas dedicadas para refactors grandes y commitear por fases.",
]
summary.quiz = [
    {"question": "¿Qué herramienta actúa como fuente de verdad visual en el flujo diseño → código?",
     "options": ["Photoshop", "Visual Studio Code", "Figma", "Notion"], "correct_idx": 2,
     "explanation": "Figma mantiene el sistema de diseño; sus tokens se traducen a variables CSS."},
    {"question": "¿Qué genera Claude Code en un proyecto Django?",
     "options": ["Solo CSS", "Modelos y migraciones", "Imágenes", "Videos"], "correct_idx": 1,
     "explanation": "Genera modelos, migraciones y código manteniendo las convenciones."},
    {"question": "¿Cómo se logra el efecto liquid glass en iOS?",
     "options": ["Con BlurView", "Con un GIF", "Con JavaScript puro", "No se puede"], "correct_idx": 0,
     "explanation": "iOS usa BlurView nativo; Android usa overlays translúcidos."},
    {"question": "¿Qué práctica reduce errores entre backend y mobile?",
     "options": ["No documentar", "Un contrato de API consistente", "Usar Excel", "Evitar tests"], "correct_idx": 1,
     "explanation": "Un contrato claro asegura que ambos consuman las mismas claves."},
    {"question": "¿Cómo conviene encarar un refactor grande?",
     "options": ["Todo de una en main", "En una rama dedicada por fases", "Sin git", "Borrando todo"], "correct_idx": 1,
     "explanation": "Rama dedicada + commits por fases permite revertir si algo falla."},
]
summary.error_msg = ""
summary.save()

print("=" * 50)
print("SEED COMPLETO ✓")
print(f"  Participantes : {Participant.objects.count()}")
print(f"  Eventos       : {Event.objects.count()}")
print(f"  Certificados  : {Certificate.objects.count()}")
print(f"  Inscripciones : {Enrollment.objects.count()}")
print(f"  Resúmenes IA  : {SessionSummary.objects.filter(status='ready').count()} listos")
print()
print("  Login demo: test@unemi.edu.ec / demo12345")
print(f"  Evento con resumen IA: '{ev_pasado.title}' (id={ev_pasado.id})")
print("=" * 50)
