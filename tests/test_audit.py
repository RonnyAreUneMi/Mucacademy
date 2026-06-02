"""Tests de auditoría automática via AuditedModelViewSet."""
import pytest


@pytest.mark.django_db
class TestAuditedCRUD:
    def test_create_logs_audit(self, admin_client, batch):
        from core.models import AuditLog
        res = admin_client.post('/api/v1/admin/sessions/', {
            'title': 'Test Audit',
            'description': '',
            'modality': 'in_person',
            'location': 'Test',
            'date': '2030-01-15',
            'start_time': '10:00',
            'end_time': '12:00',
            'capacity': 50,
            'batch': batch.id,
        }, format='json')
        assert res.status_code == 201, res.data
        assert AuditLog.objects.filter(action='CREATE').count() == 1

    def test_delete_logs_audit(self, admin_client, event):
        from core.models import AuditLog
        admin_client.delete(f'/api/v1/admin/sessions/{event.id}/')
        assert AuditLog.objects.filter(action='DELETE').count() == 1

    def test_audit_endpoint_returns_entries(self, admin_client, event):
        admin_client.post(f'/api/v1/admin/sessions/{event.id}/toggle/')
        res = admin_client.get('/api/v1/admin/audit/')
        assert res.status_code == 200
        assert res.data['count'] >= 1
