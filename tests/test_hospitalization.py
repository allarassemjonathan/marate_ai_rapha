import pytest
from unittest.mock import patch, MagicMock
import json


class TestHospitalizationRoutes:
    """Tests for all hospitalization CRUD routes."""

    @pytest.fixture(autouse=True)
    def setup_db(self, mock_db_connection):
        """Extend the conftest mock to also work with direct (non-context-manager) calls."""
        with patch('app.get_db_connection') as mock_conn:
            self.cursor = MagicMock()
            self.connection = MagicMock()

            mock_conn.return_value = self.connection
            self.connection.cursor.return_value = self.cursor

            mock_conn.return_value.__enter__ = MagicMock(return_value=self.connection)
            mock_conn.return_value.__exit__ = MagicMock(return_value=None)
            self.connection.cursor.return_value.__enter__ = MagicMock(return_value=self.cursor)
            self.connection.cursor.return_value.__exit__ = MagicMock(return_value=None)

            yield

    # ── POST /hospitalization ───────────────────────────────────

    def test_create_hospitalization_success(self, authenticated_session):
        self.cursor.fetchone.return_value = {'id': 42}
        r = authenticated_session.post('/hospitalization',
            data=json.dumps({
                'patient_id': 1,
                'date_admission': '2026-04-19T08:00',
                'medecin_traitant': 'Dr Gueye',
                'syndrome': 'Fievre',
                'constante_temperature': '39.2',
                'constante_ta': '13/8',
                'constante_fc': '95',
                'constante_poids': '68',
                'diagnostic': 'Paludisme grave',
                'observation': 'Patient conscient',
                'treatments': [
                    {'description': 'Artesunate IV', 'fait': False},
                    {'description': 'Perfalgan 1g', 'fait': False},
                ],
            }),
            content_type='application/json')

        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['status'] == 'success'
        assert data['id'] == 42
        # INSERT hospitalization + 2 INSERT treatments = at least 3 execute calls
        assert self.cursor.execute.call_count >= 3

    def test_create_hospitalization_no_patient_id(self, authenticated_session):
        r = authenticated_session.post('/hospitalization',
            data=json.dumps({'syndrome': 'Test'}),
            content_type='application/json')
        assert r.status_code == 400
        data = json.loads(r.data)
        assert data['status'] == 'error'
        assert 'patient_id' in data['message']

    def test_create_hospitalization_empty_treatments(self, authenticated_session):
        self.cursor.fetchone.return_value = {'id': 1}
        r = authenticated_session.post('/hospitalization',
            data=json.dumps({
                'patient_id': 1,
                'syndrome': 'Test',
                'treatments': [],
            }),
            content_type='application/json')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['status'] == 'success'

    def test_create_hospitalization_skips_empty_descriptions(self, authenticated_session):
        self.cursor.fetchone.return_value = {'id': 1}
        r = authenticated_session.post('/hospitalization',
            data=json.dumps({
                'patient_id': 1,
                'treatments': [
                    {'description': 'Real treatment', 'fait': False},
                    {'description': '', 'fait': False},
                    {'description': '   ', 'fait': False},
                ],
            }),
            content_type='application/json')
        assert r.status_code == 200
        # Only 1 treatment should be inserted (+ 1 hospitalization)
        assert self.cursor.execute.call_count == 2

    # ── GET /hospitalizations/<patient_id> ──────────────────────

    def test_list_hospitalizations(self, authenticated_session):
        self.cursor.fetchall.return_value = [
            {'id': 1, 'patient_id': 5, 'syndrome': 'Fievre', 'date_admission': '2026-04-19'},
            {'id': 2, 'patient_id': 5, 'syndrome': 'Grippe', 'date_admission': '2026-03-15'},
        ]
        r = authenticated_session.get('/hospitalizations/5')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert len(data) == 2

    def test_list_hospitalizations_empty(self, authenticated_session):
        self.cursor.fetchall.return_value = []
        r = authenticated_session.get('/hospitalizations/999')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data == []

    # ── GET /hospitalization/<id> ───────────────────────────────

    def test_get_hospitalization_with_treatments(self, authenticated_session):
        self.cursor.fetchone.return_value = {
            'id': 1, 'patient_id': 5, 'syndrome': 'Fievre',
            'diagnostic': 'Paludisme', 'date_admission': '2026-04-19',
        }
        self.cursor.fetchall.return_value = [
            {'id': 10, 'hospitalization_id': 1, 'ordre': 1,
             'description': 'Artesunate', 'fait': True, 'fait_par': 'Inf. Diop', 'heure': '08:00'},
            {'id': 11, 'hospitalization_id': 1, 'ordre': 2,
             'description': 'Perfalgan', 'fait': False, 'fait_par': None, 'heure': None},
        ]
        r = authenticated_session.get('/hospitalization/1')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['syndrome'] == 'Fievre'
        assert len(data['treatments']) == 2
        assert data['treatments'][0]['fait'] is True
        assert data['treatments'][1]['fait'] is False

    def test_get_hospitalization_not_found(self, authenticated_session):
        self.cursor.fetchone.return_value = None
        r = authenticated_session.get('/hospitalization/999')
        assert r.status_code == 404
        data = json.loads(r.data)
        assert data['status'] == 'error'

    # ── PUT /hospitalization/<id> ───────────────────────────────

    def test_update_hospitalization(self, authenticated_session):
        r = authenticated_session.put('/hospitalization/1',
            data=json.dumps({
                'medecin_traitant': 'Dr Sarr',
                'syndrome': 'Fievre amelioree',
                'constante_temperature': '37.2',
                'constante_ta': '12/7',
                'constante_fc': '78',
                'constante_poids': '70',
                'diagnostic': 'Paludisme en remission',
                'observation': 'Amelioration nette',
                'date_sortie': '2026-04-21T10:00',
                'observations_sortie': 'Patient gueri',
                'treatments': [
                    {'description': 'Artesunate', 'fait': True, 'fait_par': 'Inf. Diop', 'heure': '08:00'},
                ],
            }),
            content_type='application/json')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['status'] == 'success'
        # UPDATE + DELETE old treatments + INSERT new treatment = 3 calls
        assert self.cursor.execute.call_count >= 3

    # ── DELETE /hospitalization/<id> ────────────────────────────

    def test_delete_hospitalization(self, authenticated_session):
        r = authenticated_session.delete('/hospitalization/1')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['status'] == 'deleted'
        self.cursor.execute.assert_called()

    # ── Auth required ──────────────────────────────────────────

    def test_hospitalization_requires_login(self, client):
        routes = [
            ('POST', '/hospitalization'),
            ('GET', '/hospitalizations/1'),
            ('GET', '/hospitalization/1'),
            ('PUT', '/hospitalization/1'),
            ('DELETE', '/hospitalization/1'),
        ]
        for method, url in routes:
            r = getattr(client, method.lower())(url, follow_redirects=False)
            assert r.status_code == 302, f"{method} {url} should redirect when not logged in"
            assert '/login' in r.location, f"{method} {url} should redirect to /login"
