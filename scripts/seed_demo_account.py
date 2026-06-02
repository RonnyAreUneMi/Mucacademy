"""Seed datos demo para la cuenta de tesis (test@unemi.edu.ec).

Uso:
    python manage.py shell < scripts/seed_demo_account.py
"""
from datetime import date, time, timedelta

from django.utils import timezone

from core.models import (
    Certificate, Enrollment, CertificateBatch, Participant,
    Event,
)

EMAIL = "test@unemi.edu.ec"
p = Participant.objects.get(email=EMAIL)
print(f"Participante: {p.id} {p.full_name}")

# ── Lote + 3 certificados ────────────────────────────────────────
batch, _ = CertificateBatch.objects.get_or_create(
    name="Seminario Demo Tesis 2026",
)
cursos = [
    ("Introducción a la Inteligencia Artificial", date(2026, 3, 15), 12),
    ("Bases de Datos para Investigación",        date(2026, 3, 22), 8),
    ("Fundamentos de UX en Aplicaciones Móviles", date(2026, 4, 5),  6),
]
for curso, fecha, horas in cursos:
    Certificate.objects.get_or_create(
        batch=batch,
        national_id=p.national_id or "0000000000",
        email=p.email,
        course=curso,
        defaults={
            "participant": p,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "course_date": fecha,
            "hours": horas,
        },
    )
print(f"Certificados de {EMAIL}: {Certificate.objects.filter(email=EMAIL).count()}")

# ── 2 eventos próximos (1 inscrito, 1 disponible) ────────────────
hoy = timezone.localdate()
ev_inscrito, _ = Event.objects.get_or_create(
    title="Webinar · Tendencias de IA en Educación",
    defaults={
        "batch": batch,
        "description": "Sesión virtual con expertos en aplicaciones de IA en aulas universitarias.",
        "modality": "virtual",
        "virtual_platform": "meet",
        "meeting_url": "https://meet.google.com/abc-defg-hij",
        "date": hoy + timedelta(days=3),
        "start_time": time(18, 0),
        "end_time": time(20, 0),
    },
)
Enrollment.objects.get_or_create(participant=p, event=ev_inscrito)

ev_disponible, _ = Event.objects.get_or_create(
    title="Taller · Diseño de Tesis con Métodos Mixtos",
    defaults={
        "batch": batch,
        "description": "Taller presencial en Auditorio FACS UNEMI. Cupos limitados.",
        "modality": "in_person",
        "location": "Auditorio FACS · Bloque B",
        "date": hoy + timedelta(days=10),
        "start_time": time(9, 0),
        "end_time": time(12, 0),
    },
)
print(f"Eventos: inscrito={ev_inscrito.id} disponible={ev_disponible.id}")
print("Demo seed OK ✓")
