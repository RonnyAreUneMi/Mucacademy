"""Fixtures compartidos para todos los tests."""
import pytest
from rest_framework.test import APIClient

from tests.factories import (
    UserFactory, SuperAdminFactory,
    BatchFactory, ParticipantFactory, EventFactory, CertificateFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return UserFactory()


@pytest.fixture
def super_admin_user(db):
    return SuperAdminFactory()


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def super_admin_client(api_client, super_admin_user):
    api_client.force_authenticate(user=super_admin_user)
    return api_client


@pytest.fixture
def batch(db):
    return BatchFactory()


@pytest.fixture
def participant(db):
    return ParticipantFactory()


@pytest.fixture
def event(db, batch):
    return EventFactory(batch=batch)


@pytest.fixture
def certificate(db, batch, participant):
    return CertificateFactory(batch=batch, participant=participant)
