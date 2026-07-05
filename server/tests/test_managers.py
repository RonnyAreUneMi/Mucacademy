"""Tests de QuerySets y Managers custom."""
import pytest

from tests.factories import CertificateFactory, ParticipantFactory, EventFactory


@pytest.mark.django_db
class TestCertificateManager:
    def test_search_by_national_id(self):
        c1 = CertificateFactory(national_id='0912345678')
        CertificateFactory(national_id='0999999999')
        from core.models import Certificate
        results = Certificate.objects.search('0912')
        assert c1 in results
        assert results.count() == 1

    def test_search_empty_returns_none(self):
        CertificateFactory()
        from core.models import Certificate
        assert Certificate.objects.search('').count() == 0

    def test_downloaded_filters_by_count(self):
        CertificateFactory(download_count=0)
        CertificateFactory(download_count=5)
        from core.models import Certificate
        assert Certificate.objects.downloaded().count() == 1

    def test_with_relations_prefetches(self, django_assert_max_num_queries):
        CertificateFactory()
        from core.models import Certificate
        with django_assert_max_num_queries(2):
            list(Certificate.objects.with_relations())

    def test_search_multi_token_is_AND_not_OR(self):
        """'Adriana Carolina' NO debe matchear a 'Jacqueline Gonzalez' ni a 'Adriana Smith'."""
        from core.models import Certificate
        # Match exacto (ambas palabras)
        match = CertificateFactory(first_name='ADRIANA CAROLINA', last_name='CORTEZ')
        # Solo una palabra
        only_adriana = CertificateFactory(first_name='ADRIANA', last_name='VILLACRES')
        only_carolina = CertificateFactory(first_name='CAROLINA', last_name='LUCAS')
        # Ninguna palabra
        CertificateFactory(first_name='JACQUELINE', last_name='GONZALEZ')

        results = list(Certificate.objects.search('Adriana Carolina'))
        assert match in results
        assert only_adriana not in results
        assert only_carolina not in results
        assert len(results) == 1

    def test_search_dedupes_by_person_course(self):
        """Dos certificados del mismo (national_id, course) → solo uno aparece tras dedupe."""
        from core.models import Certificate
        CertificateFactory(national_id='0912345678', course='MATH', first_name='A')
        dup = CertificateFactory(national_id='0912345678', course='MATH', first_name='A')
        different = CertificateFactory(national_id='0912345678', course='FISICA', first_name='A')
        ids = set(Certificate.objects.deduped_by_person_course().values_list('id', flat=True))
        assert dup.id in ids  # el más reciente (mayor id) queda
        assert different.id in ids  # distinto curso queda
        assert len(ids) == 2


@pytest.mark.django_db
class TestParticipantManager:
    def test_search_name_tokens(self):
        ParticipantFactory(first_name='Ana', last_name='García')
        ParticipantFactory(first_name='Juan', last_name='Pérez')
        from core.models import Participant
        results = Participant.objects.search('Ana')
        assert results.count() == 1

    def test_leaders_filter(self):
        ParticipantFactory(is_leader=False)
        ParticipantFactory(is_leader=True)
        from core.models import Participant
        assert Participant.objects.leaders().count() == 1


@pytest.mark.django_db
class TestEventManager:
    def test_upcoming_excludes_past(self):
        from datetime import date, timedelta
        EventFactory(date=date.today() - timedelta(days=1))  # past
        future = EventFactory(date=date.today() + timedelta(days=1))
        from core.models import Event
        upcoming = Event.objects.upcoming()
        assert future in upcoming
        assert upcoming.count() == 1

    def test_past_reverse(self):
        from datetime import date, timedelta
        past = EventFactory(date=date.today() - timedelta(days=5))
        EventFactory(date=date.today() + timedelta(days=3))
        from core.models import Event
        assert past in Event.objects.past()
