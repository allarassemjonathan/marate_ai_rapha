"""
Marate AI - Comprehensive Platform Tests
=========================================
Run:  pytest marate_testing.py -v
All tests passing = the platform is working.
"""
import pytest
from unittest.mock import patch, MagicMock
import json
from app import app


# ── Fixtures (self-contained, no conftest dependency) ───────────

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture
def mock_db():
    """Mock DB that works with both context-manager and direct-call patterns."""
    with patch('app.get_db_connection') as mock_conn:
        mock_cursor = MagicMock()
        mock_connection = MagicMock()

        # Direct call pattern: conn = get_db_connection()
        mock_conn.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor

        # Context manager pattern: with get_db_connection() as conn:
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_connection)
        mock_conn.return_value.__exit__ = MagicMock(return_value=None)
        mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=None)

        yield mock_cursor


@pytest.fixture
def doctor(client):
    with client.session_transaction() as s:
        s['logged_in'] = True
        s['username'] = 'Dr_Test'
        s['user_type'] = 'medecins'
    return client


@pytest.fixture
def nurse(client):
    with client.session_transaction() as s:
        s['logged_in'] = True
        s['username'] = 'infirmiers'
        s['user_type'] = 'infirmiers'
    return client


@pytest.fixture
def receptionist(client):
    with client.session_transaction() as s:
        s['logged_in'] = True
        s['username'] = 'receptionistes'
        s['user_type'] = 'receptionistes'
    return client


MOCK_COLUMNS = [
    {'column_name': 'id', 'display_name': 'ID', 'data_type': 'SERIAL'},
    {'column_name': 'name', 'display_name': 'Nom', 'data_type': 'TEXT'},
    {'column_name': 'adresse', 'display_name': 'Adresse', 'data_type': 'TEXT'},
    {'column_name': 'age', 'display_name': 'Age', 'data_type': 'INTEGER'},
    {'column_name': 'age_years', 'display_name': 'Age annees', 'data_type': 'INTEGER'},
    {'column_name': 'age_months', 'display_name': 'Age mois', 'data_type': 'INTEGER'},
    {'column_name': 'age_days', 'display_name': 'Age jours', 'data_type': 'INTEGER'},
    {'column_name': 'poids', 'display_name': 'Poids', 'data_type': 'REAL'},
    {'column_name': 'taille', 'display_name': 'Taille', 'data_type': 'REAL'},
    {'column_name': 'temperature', 'display_name': 'Temperature', 'data_type': 'TEXT'},
    {'column_name': 'tension_arterielle', 'display_name': 'Tension', 'data_type': 'TEXT'},
    {'column_name': 'signature', 'display_name': 'Signature', 'data_type': 'TEXT'},
    {'column_name': 'created_at', 'display_name': 'Date', 'data_type': 'DATE'},
]


@pytest.fixture(autouse=True)
def mock_columns():
    with patch('app.get_visible_columns', return_value=MOCK_COLUMNS):
        yield


def _post_json(client, url, data):
    return client.post(url, data=json.dumps(data), content_type='application/json')


def _put_json(client, url, data):
    return client.put(url, data=json.dumps(data), content_type='application/json')


# ── Auth Tests ──────────────────────────────────────────────────

class TestAuth:

    def test_login_page_loads(self, client):
        r = client.get('/login')
        assert r.status_code == 200

    def test_unauthenticated_redirects_to_login(self, client):
        r = client.get('/', follow_redirects=False)
        assert r.status_code == 302
        assert '/login' in r.location

    def test_logout_clears_session(self, doctor):
        r = doctor.get('/logout', follow_redirects=False)
        assert r.status_code == 302
        r = doctor.get('/', follow_redirects=False)
        assert r.status_code == 302
        assert '/login' in r.location


# ── Patient CRUD Tests ──────────────────────────────────────────

class TestPatientCRUD:

    def test_add_patient_success(self, doctor, mock_db):
        with patch('app.email_reception'):
            r = _post_json(doctor, '/add', {
                'name': 'Amadou Diallo',
                'adresse': 'Dakar',
                'age_years': '30',
                'age_months': '0',
                'age_days': '0',
            })
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['status'] == 'success'

    def test_add_patient_missing_name(self, doctor, mock_db):
        r = _post_json(doctor, '/add', {'adresse': 'Dakar'})
        assert r.status_code == 400
        data = json.loads(r.data)
        assert 'error' in data['status']

    def test_search_patients(self, doctor, mock_db):
        mock_db.fetchall.return_value = [
            {'id': 1, 'name': 'Amadou Diallo', 'adresse': 'Dakar', 'age': 30, 'created_at': '2026-01-01'},
        ]
        r = doctor.get('/search?q=Amadou')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert len(data) >= 1
        assert data[0]['name'] == 'Amadou Diallo'

    def test_search_empty_query(self, doctor, mock_db):
        mock_db.fetchall.return_value = [
            {'id': 1, 'name': 'Patient A', 'created_at': '2026-01-01'},
            {'id': 2, 'name': 'Patient B', 'created_at': '2026-01-02'},
        ]
        r = doctor.get('/search?q=')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert len(data) >= 1

    def test_get_patient(self, doctor, mock_db):
        mock_db.fetchone.return_value = {
            'id': 1, 'name': 'Amadou Diallo', 'signature': 'Dr Test',
            'adresse': 'Dakar', 'age': 30,
        }
        r = doctor.get('/get_patient/1')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['name'] == 'Amadou Diallo'

    def test_update_patient_success(self, doctor, mock_db):
        r = _put_json(doctor, '/update/1', {
            'name': 'Amadou Diallo',
            'adresse': 'Saint-Louis',
            'temperature': '38.5',
        })
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['status'] == 'success'

    def test_update_patient_missing_name(self, doctor, mock_db):
        r = _put_json(doctor, '/update/1', {'adresse': 'Dakar'})
        assert r.status_code == 400

    def test_delete_patient(self, doctor, mock_db):
        mock_db.fetchall.return_value = [{'id': 1, 'name': 'Amadou Diallo'}]
        r = doctor.delete('/delete/1')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['status'] == 'deleted'


# ── Access Control Tests ────────────────────────────────────────

class TestAccessControl:

    def test_doctor_blocked_from_other_doctors_patient(self, doctor, mock_db):
        mock_db.fetchone.return_value = {
            'id': 1, 'name': 'Patient X', 'signature': 'Dr Other',
        }
        r = doctor.get('/get_patient/1')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data.get('status') == 'error'

    def test_nurse_can_access_any_patient(self, nurse, mock_db):
        mock_db.fetchone.return_value = {
            'id': 1, 'name': 'Patient X', 'signature': 'Dr Other',
            'adresse': 'Dakar', 'age': 25,
        }
        r = nurse.get('/get_patient/1')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['name'] == 'Patient X'

    def test_unsigned_patient_accessible_by_any_doctor(self, doctor, mock_db):
        mock_db.fetchone.return_value = {
            'id': 1, 'name': 'New Patient', 'signature': None,
            'adresse': 'Dakar',
        }
        r = doctor.get('/get_patient/1')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['name'] == 'New Patient'


# ── Invoice Tests ───────────────────────────────────────────────

class TestInvoice:

    def test_generate_invoice_success(self, doctor, mock_db):
        invoice_data = {
            'meta': {
                'nom': 'Diallo', 'prenom': 'Amadou',
                'pourcentage': '80', 'police': '12345',
            },
            'sections': [{
                'titre': 'Consultation',
                'articles': [{'libelle': 'Examen', 'quantite': 1, 'montant': 5000}],
            }],
        }
        with patch('app.InvoicePDF') as mock_pdf:
            mock_pdf.return_value = MagicMock()
            with patch('tempfile.mktemp', return_value='/tmp/test.pdf'):
                with patch('app.send_file', return_value=MagicMock(status_code=200)) as mock_send:
                    mock_send.return_value.status_code = 200
                    r = _post_json(doctor, '/generate_invoice/1', invoice_data)
                    assert r.status_code == 200

    def test_generate_invoice_missing_meta(self, doctor):
        r = _post_json(doctor, '/generate_invoice/1', {
            'sections': [{'titre': 'Test', 'articles': []}],
        })
        assert r.status_code == 400
        data = json.loads(r.data)
        assert data['status'] == 'error'

    def test_generate_invoice_missing_sections(self, doctor):
        r = _post_json(doctor, '/generate_invoice/1', {
            'meta': {'nom': 'Test', 'prenom': 'User', 'pourcentage': '80'},
        })
        assert r.status_code == 400


# ── Hospitalization Tests ───────────────────────────────────────

class TestHospitalization:

    def test_create_hospitalization(self, doctor, mock_db):
        mock_db.fetchone.return_value = {'id': 1}
        r = _post_json(doctor, '/hospitalization', {
            'patient_id': 10,
            'date_admission': '2026-04-19T10:00',
            'medecin_traitant': 'Dr Gueye',
            'syndrome': 'Fievre',
            'constante_temperature': '39',
            'constante_ta': '12/8',
            'constante_fc': '90',
            'constante_poids': '70',
            'diagnostic': 'Paludisme',
            'observation': 'Patient conscient',
            'treatments': [
                {'description': 'Perfalgan IV', 'fait': False, 'fait_par': '', 'heure': ''},
                {'description': 'Artesunate', 'fait': False, 'fait_par': '', 'heure': ''},
            ],
        })
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['status'] == 'success'
        assert data['id'] == 1

    def test_create_hospitalization_missing_patient(self, doctor, mock_db):
        r = _post_json(doctor, '/hospitalization', {
            'syndrome': 'Test',
        })
        assert r.status_code == 400
        data = json.loads(r.data)
        assert data['status'] == 'error'

    def test_list_hospitalizations(self, doctor, mock_db):
        mock_db.fetchall.return_value = [
            {'id': 1, 'patient_id': 10, 'syndrome': 'Fievre', 'date_admission': '2026-04-19'},
            {'id': 2, 'patient_id': 10, 'syndrome': 'Grippe', 'date_admission': '2026-03-01'},
        ]
        r = doctor.get('/hospitalizations/10')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert len(data) == 2

    def test_get_hospitalization(self, doctor, mock_db):
        mock_db.fetchone.return_value = {
            'id': 1, 'patient_id': 10, 'syndrome': 'Fievre',
            'diagnostic': 'Paludisme', 'date_admission': '2026-04-19',
        }
        mock_db.fetchall.return_value = [
            {'id': 1, 'hospitalization_id': 1, 'ordre': 1, 'description': 'Perfalgan',
             'fait': True, 'fait_par': 'Nurse A', 'heure': '10:00'},
        ]
        r = doctor.get('/hospitalization/1')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['syndrome'] == 'Fievre'
        assert len(data['treatments']) == 1
        assert data['treatments'][0]['description'] == 'Perfalgan'

    def test_get_hospitalization_not_found(self, doctor, mock_db):
        mock_db.fetchone.return_value = None
        r = doctor.get('/hospitalization/999')
        assert r.status_code == 404

    def test_update_hospitalization(self, doctor, mock_db):
        r = _put_json(doctor, '/hospitalization/1', {
            'medecin_traitant': 'Dr Gueye',
            'syndrome': 'Fievre amelioree',
            'constante_temperature': '37.5',
            'constante_ta': '12/7',
            'constante_fc': '80',
            'constante_poids': '70',
            'diagnostic': 'Paludisme en remission',
            'observation': 'Amelioration',
            'date_sortie': '2026-04-21T14:00',
            'observations_sortie': 'Guerison',
            'treatments': [
                {'description': 'Perfalgan IV', 'fait': True, 'fait_par': 'Infirmier A', 'heure': '10:00'},
                {'description': 'Artesunate', 'fait': True, 'fait_par': 'Infirmier B', 'heure': '14:00'},
            ],
        })
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['status'] == 'success'

    def test_delete_hospitalization(self, doctor, mock_db):
        r = doctor.delete('/hospitalization/1')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['status'] == 'deleted'


# ── Full Workflow Test ──────────────────────────────────────────

class TestFullWorkflow:

    def test_patient_lifecycle(self, doctor, mock_db):
        """Add -> Search -> Get -> Update -> Invoice -> Delete"""

        # 1. Add patient
        with patch('app.email_reception'):
            r = _post_json(doctor, '/add', {
                'name': 'Fatou Sall',
                'adresse': 'Rufisque',
                'age_years': '45',
                'age_months': '0',
                'age_days': '0',
            })
        assert r.status_code == 200

        # 2. Search
        mock_db.fetchall.return_value = [
            {'id': 1, 'name': 'Fatou Sall', 'adresse': 'Rufisque', 'age': 45, 'created_at': '2026-04-19'},
        ]
        r = doctor.get('/search?q=Fatou')
        assert r.status_code == 200
        patients = json.loads(r.data)
        assert len(patients) == 1

        # 3. Get patient
        mock_db.fetchone.return_value = {
            'id': 1, 'name': 'Fatou Sall', 'signature': 'Dr Test',
            'adresse': 'Rufisque', 'age': 45,
        }
        r = doctor.get('/get_patient/1')
        assert r.status_code == 200

        # 4. Update — fetchall will be called for column metadata
        mock_db.fetchall.return_value = [
            {'column_name': 'name', 'display_name': 'Nom', 'data_type': 'TEXT'},
            {'column_name': 'temperature', 'display_name': 'Temperature', 'data_type': 'TEXT'},
            {'column_name': 'adresse', 'display_name': 'Adresse', 'data_type': 'TEXT'},
        ]
        r = _put_json(doctor, '/update/1', {
            'name': 'Fatou Sall',
            'temperature': '38.2',
        })
        assert r.status_code == 200

        # 5. Invoice
        with patch('app.InvoicePDF') as mock_pdf:
            mock_pdf.return_value = MagicMock()
            with patch('tempfile.mktemp', return_value='/tmp/test.pdf'):
                with patch('app.send_file', return_value=MagicMock(status_code=200)):
                    r = _post_json(doctor, '/generate_invoice/1', {
                        'meta': {'nom': 'Sall', 'prenom': 'Fatou', 'pourcentage': '80'},
                        'sections': [{'titre': 'Consultation',
                                      'articles': [{'libelle': 'Examen', 'quantite': 1, 'montant': 3000}]}],
                    })
                    assert r.status_code == 200

        # 6. Delete
        mock_db.fetchall.return_value = [{'id': 1, 'name': 'Fatou Sall'}]
        r = doctor.delete('/delete/1')
        assert r.status_code == 200
        assert json.loads(r.data)['status'] == 'deleted'

    def test_hospitalization_lifecycle(self, doctor, mock_db):
        """Create -> Get -> Update (nurse checks treatments) -> Discharge -> Delete"""

        # 1. Create
        mock_db.fetchone.return_value = {'id': 5}
        r = _post_json(doctor, '/hospitalization', {
            'patient_id': 1,
            'medecin_traitant': 'Dr Gueye',
            'syndrome': 'Douleurs abdominales',
            'diagnostic': 'Appendicite',
            'treatments': [
                {'description': 'Ceftriaxone 1g IV', 'fait': False},
                {'description': 'Perfalgan 1g IV', 'fait': False},
            ],
        })
        assert r.status_code == 200
        assert json.loads(r.data)['id'] == 5

        # 2. Get
        mock_db.fetchone.return_value = {
            'id': 5, 'patient_id': 1, 'syndrome': 'Douleurs abdominales',
            'diagnostic': 'Appendicite', 'date_admission': '2026-04-19',
        }
        mock_db.fetchall.return_value = [
            {'id': 10, 'hospitalization_id': 5, 'ordre': 1,
             'description': 'Ceftriaxone 1g IV', 'fait': False, 'fait_par': None, 'heure': None},
        ]
        r = doctor.get('/hospitalization/5')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['diagnostic'] == 'Appendicite'

        # 3. Update with discharge
        r = _put_json(doctor, '/hospitalization/5', {
            'medecin_traitant': 'Dr Gueye',
            'syndrome': 'Douleurs abdominales',
            'diagnostic': 'Appendicite',
            'date_sortie': '2026-04-21T10:00',
            'observations_sortie': 'Patient gueri',
            'treatments': [
                {'description': 'Ceftriaxone 1g IV', 'fait': True, 'fait_par': 'Inf. Ndiaye', 'heure': '08:00'},
                {'description': 'Perfalgan 1g IV', 'fait': True, 'fait_par': 'Inf. Ndiaye', 'heure': '14:00'},
            ],
        })
        assert r.status_code == 200

        # 4. Delete
        r = doctor.delete('/hospitalization/5')
        assert r.status_code == 200
        assert json.loads(r.data)['status'] == 'deleted'
