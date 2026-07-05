"""Tests de autenticación JWT."""
import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAuth:
    def test_login_with_valid_credentials(self, api_client, admin_user):
        res = api_client.post('/api/v1/auth/login/', {
            'username': admin_user.username,
            'password': 'testpass123',
        }, format='json')
        assert res.status_code == 200
        assert 'access' in res.data
        assert 'refresh' in res.data
        assert res.data['user']['username'] == admin_user.username

    def test_login_with_invalid_password(self, api_client, admin_user):
        res = api_client.post('/api/v1/auth/login/', {
            'username': admin_user.username,
            'password': 'wrong',
        }, format='json')
        assert res.status_code == 401

    def test_me_requires_auth(self, api_client):
        res = api_client.get('/api/v1/auth/me/')
        assert res.status_code == 401

    def test_me_returns_user_info(self, admin_client, admin_user):
        res = admin_client.get('/api/v1/auth/me/')
        assert res.status_code == 200
        assert res.data['username'] == admin_user.username


@pytest.mark.django_db
class TestPermissions:
    def test_admin_endpoints_reject_anonymous(self, api_client):
        for path in ['/api/v1/admin/sessions/', '/api/v1/admin/users/',
                     '/api/v1/admin/dashboard/']:
            res = api_client.get(path)
            assert res.status_code == 401, f'{path} should be 401'

    def test_public_endpoints_allow_anonymous(self, api_client):
        for path in ['/api/v1/public/sessions/', '/api/v1/public/stats/']:
            res = api_client.get(path)
            assert res.status_code == 200, f'{path} should be 200'
