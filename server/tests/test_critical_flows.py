"""Tests críticos del dominio CertifAI · happy paths + edge cases.

Cubre los 3 flujos que NO PUEDEN FALLAR en producción:
  1. Verificación pública de certificado por hash
  2. Inscripción de participante a evento
  3. Generación de lote de certificados desde sesión
  4. Auth de cuenta pública (registro + login)

Cada test es independiente (--reuse-db está OK porque no compartimos state).
"""
from datetime import date, timedelta
import uuid

import pytest

from core.models import Certificate, Enrollment, Participant
from tests.factories import (
    BatchFactory, ParticipantFactory, EventFactory, CertificateFactory,
)


# ════════════════════════════════════════════════════════════════
#  1 · Verificación pública por hash (3 tests)
# ════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_verify_certificate_happy_path(api_client):
    """Hash válido devuelve 200 con datos del certificado."""
    cert = CertificateFactory(course='Curso de Prueba', hours=40)
    res = api_client.get(f'/api/v1/public/verify/{cert.verification_hash}/')
    assert res.status_code == 200
    data = res.json()
    assert data['found'] is True
    assert data['certificate']['first_name'] == cert.first_name
    assert data['certificate']['course'] == 'Curso de Prueba'


@pytest.mark.django_db
def test_verify_certificate_invalid_hash_returns_404(api_client):
    """Hash inexistente devuelve 404 — no filtra que el hash existe o no."""
    fake_hash = uuid.uuid4()
    res = api_client.get(f'/api/v1/public/verify/{fake_hash}/')
    assert res.status_code == 404


@pytest.mark.django_db
def test_verify_certificate_increments_search_counter(api_client):
    """Cada verify incrementa search_count para analítica."""
    cert = CertificateFactory()
    initial = cert.search_count
    api_client.get(f'/api/v1/public/verify/{cert.verification_hash}/')
    cert.refresh_from_db()
    assert cert.search_count == initial + 1


# ════════════════════════════════════════════════════════════════
#  2 · Inscripción a evento (cuenta de participante)  (3 tests)
# ════════════════════════════════════════════════════════════════

@pytest.fixture
def participant_logged_in(db, client):
    """Crea participante con cuenta y lo deja logueado vía sesión Django."""
    p = ParticipantFactory(email='estudiante@unemi.edu.ec')
    p.set_password('test1234')
    p.save()
    session = client.session
    session['participant_id'] = p.id
    session.save()
    return p


@pytest.mark.django_db
def test_inscripcion_evento_creates_enrollment(client, participant_logged_in, settings):
    """POST a /cuenta/eventos/<id>/inscribir/ crea Enrollment."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    s = EventFactory(is_active=True, date=date.today() + timedelta(days=7))
    res = client.post(f'/cuenta/eventos/{s.id}/inscribir/', follow=False)
    assert res.status_code in (302, 200)
    assert Enrollment.objects.filter(
        participant=participant_logged_in, event=s
    ).exists()


@pytest.mark.django_db
def test_inscripcion_evento_idempotent(client, participant_logged_in, settings):
    """Inscribirse 2 veces no crea duplicado (get_or_create)."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    s = EventFactory(is_active=True, date=date.today() + timedelta(days=7))
    client.post(f'/cuenta/eventos/{s.id}/inscribir/')
    client.post(f'/cuenta/eventos/{s.id}/inscribir/')
    count = Enrollment.objects.filter(
        participant=participant_logged_in, event=s
    ).count()
    assert count == 1


@pytest.mark.django_db
def test_inscripcion_evento_inactiva_returns_404(client, participant_logged_in):
    """No se puede inscribir a una sesión is_active=False."""
    s = EventFactory(is_active=False)
    res = client.post(f'/cuenta/eventos/{s.id}/inscribir/')
    assert res.status_code == 404
    assert not Enrollment.objects.filter(participant=participant_logged_in).exists()


# ════════════════════════════════════════════════════════════════
#  3 · Generación de lote desde sesión (3 tests)
# ════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_generate_batch_creates_certificates_and_links_batch(super_admin_client, settings):
    """Happy path: 3 confirmados → batch con 3 certs + event.batch enlazado."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    s = EventFactory(is_active=True, date=date.today(), batch=None)
    for i in range(3):
        p = ParticipantFactory(email=f'p{i}@test.com', national_id='')
        Enrollment.objects.create(participant=p, event=s, confirmed=True)

    res = super_admin_client.post(
        f'/api/v1/admin/sessions/{s.id}/generate-batch/',
        {'faculty': 'FACI'}, format='json',
    )
    assert res.status_code == 200, res.content
    data = res.json()
    assert data['certificates_created'] == 3

    s.refresh_from_db()
    assert s.batch_id is not None
    assert Certificate.objects.filter(batch=s.batch).count() == 3
    # Cada cert tiene hash único
    hashes = list(Certificate.objects.filter(batch=s.batch).values_list('verification_hash', flat=True))
    assert len(set(hashes)) == 3


@pytest.mark.django_db
def test_generate_batch_409_if_already_has_batch(super_admin_client):
    """Si la sesión ya tiene batch, devuelve 409 — no crea uno nuevo."""
    s = EventFactory(is_active=True, batch=BatchFactory())
    res = super_admin_client.post(
        f'/api/v1/admin/sessions/{s.id}/generate-batch/',
        {'faculty': 'FACI'}, format='json',
    )
    assert res.status_code == 409


@pytest.mark.django_db
def test_generate_batch_404_if_no_confirmados(super_admin_client):
    """Sin participantes confirmados, devuelve 404 con mensaje claro."""
    s = EventFactory(is_active=True, batch=None)
    s.refresh_from_db()
    res = super_admin_client.post(
        f'/api/v1/admin/sessions/{s.id}/generate-batch/',
        {'faculty': 'FACI'}, format='json',
    )
    assert res.status_code == 404
    assert 'confirmados' in res.json().get('error', '').lower()


# ════════════════════════════════════════════════════════════════
#  4 · Auth de cuenta pública (3 tests)
# ════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_register_creates_participant_with_password_hash(client, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    res = client.post('/cuenta/register/', {
        'first_name': 'Juan', 'last_name': 'Pérez',
        'email': 'juan@unemi.edu.ec',
        'national_id': '', 'phone': '',  # opcionales
        'password': 'secret123', 'password2': 'secret123',
    })
    assert res.status_code == 302  # redirect a dashboard tras login
    p = Participant.objects.get(email='juan@unemi.edu.ec')
    assert p.has_account
    assert p.password_hash != ''
    assert p.check_password('secret123')


@pytest.mark.django_db
def test_register_rejects_password_mismatch(client):
    """Si password != password2, no crea cuenta."""
    res = client.post('/cuenta/register/', {
        'first_name': 'X', 'last_name': 'Y', 'email': 'x@y.com',
        'password': 'aaaaaa', 'password2': 'bbbbbb',
    })
    # Re-render del form (200) — sin crear participante
    assert res.status_code == 200
    assert not Participant.objects.filter(email='x@y.com').exists()


@pytest.mark.django_db
def test_login_correct_credentials_creates_session(client):
    """Login válido pone participant_id en la sesión."""
    p = ParticipantFactory(email='login@test.com')
    p.set_password('test1234')
    p.save()
    res = client.post('/cuenta/login/', {
        'email': 'login@test.com', 'password': 'test1234',
    })
    assert res.status_code == 302
    assert client.session.get('participant_id') == p.id


@pytest.mark.django_db
def test_login_wrong_password_keeps_no_session(client):
    """Password incorrecto no setea sesión."""
    p = ParticipantFactory(email='wrong@test.com')
    p.set_password('test1234')
    p.save()
    res = client.post('/cuenta/login/', {
        'email': 'wrong@test.com', 'password': 'WRONG',
    })
    assert res.status_code == 200  # re-render del form
    assert client.session.get('participant_id') is None
