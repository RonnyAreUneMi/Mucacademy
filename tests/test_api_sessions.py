"""Tests de API de sesiones (CRUD + custom actions + auditoría)."""
import pytest

from tests.factories import EventFactory


@pytest.mark.django_db
class TestEventAPI:
    def test_list_requires_admin(self, api_client):
        res = api_client.get('/api/v1/admin/sessions/')
        assert res.status_code == 401

    def test_admin_can_list(self, admin_client):
        EventFactory()
        EventFactory()
        res = admin_client.get('/api/v1/admin/sessions/')
        assert res.status_code == 200
        assert res.data['count'] == 2

    def test_toggle_flips_is_active(self, admin_client, event):
        assert event.is_active is True
        res = admin_client.post(f'/api/v1/admin/sessions/{event.id}/toggle/')
        assert res.status_code == 200
        assert res.data['is_active'] is False
        event.refresh_from_db()
        assert event.is_active is False

    def test_toggle_creates_audit_entry(self, admin_client, event):
        from core.models import AuditLog
        before = AuditLog.objects.filter(action='UPDATE').count()
        admin_client.post(f'/api/v1/admin/sessions/{event.id}/toggle/')
        after = AuditLog.objects.filter(action='UPDATE').count()
        assert after == before + 1

    def test_delete_rejects_with_enrollments(self, admin_client, event, participant):
        from core.models import Enrollment
        Enrollment.objects.create(
            event=event, participant=participant, confirmed=True,
        )
        res = admin_client.delete(f'/api/v1/admin/sessions/{event.id}/')
        assert res.status_code == 409
        assert 'error' in res.data


@pytest.mark.django_db
class TestPublicEventAPI:
    def test_upcoming_is_public(self, api_client):
        EventFactory()
        res = api_client.get('/api/v1/public/sessions/upcoming/')
        assert res.status_code == 200
