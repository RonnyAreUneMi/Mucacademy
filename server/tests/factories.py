"""Factories para tests (factory-boy)."""
from datetime import date, time, timedelta
import uuid

import factory
from factory.django import DjangoModelFactory

from core.models import (
    User, CertificateBatch, Participant, Certificate, Event,
)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'admin{n}')
    email = factory.Sequence(lambda n: f'admin{n}@example.com')
    first_name = 'Admin'
    last_name = 'User'
    is_staff = True
    is_superuser = False
    is_active = True
    role = 'admin'

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        obj.set_password(extracted or 'testpass123')
        if create:
            obj.save()


class SuperAdminFactory(UserFactory):
    is_superuser = True
    role = 'superadmin'


class BatchFactory(DjangoModelFactory):
    class Meta:
        model = CertificateBatch

    name = factory.Sequence(lambda n: f'Lote Test {n}')
    faculty = 'FACI'
    template = 'classic'
    is_active = True


class ParticipantFactory(DjangoModelFactory):
    class Meta:
        model = Participant

    national_id = factory.Sequence(lambda n: f'09{n:08d}')
    first_name = 'Juan'
    last_name = 'Pérez'
    email = factory.Sequence(lambda n: f'juan{n}@test.com')
    phone = '0999999999'
    is_leader = False


class EventFactory(DjangoModelFactory):
    class Meta:
        model = Event

    batch = factory.SubFactory(BatchFactory)
    title = factory.Sequence(lambda n: f'Sesión Test {n}')
    description = 'Descripción de prueba'
    date = factory.LazyFunction(lambda: date.today() + timedelta(days=7))
    start_time = time(10, 0)
    end_time = time(12, 0)
    capacity = 50
    modality = 'in_person'
    location = 'Auditorio Test'
    is_active = True


class CertificateFactory(DjangoModelFactory):
    class Meta:
        model = Certificate

    batch = factory.SubFactory(BatchFactory)
    participant = factory.SubFactory(ParticipantFactory)
    national_id = factory.Sequence(lambda n: f'09{n:08d}')
    first_name = 'Juan'
    last_name = 'Pérez'
    email = factory.Sequence(lambda n: f'juan{n}@test.com')
    course = 'Curso de Prueba'
    course_date = factory.LazyFunction(date.today)
    hours = 40
    verification_hash = factory.LazyFunction(lambda: str(uuid.uuid4()))
