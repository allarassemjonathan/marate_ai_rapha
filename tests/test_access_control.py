import pytest
from unittest.mock import patch, MagicMock
import json

class TestAccessControl:
    """Test role-based access control and permissions"""
    
    def test_doctor_can_access_own_patient(self, authenticated_session, mock_db_connection):
        """Test doctor can access their own patient"""
        # Mock patient with matching signature
        mock_patient = {
            'id': 1,
            'name': 'Test Patient',
            'signature': 'Dr Test',  # Matches session username
            'adresse': 'Test Address'
        }
        mock_db_connection.fetchone.return_value = mock_patient
        
        response = authenticated_session.get('/get_patient/1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['name'] == 'Test Patient'
    
    def test_doctor_cannot_access_other_patient(self, authenticated_session, mock_db_connection):
        """Test doctor cannot access another doctor's patient"""
        # Mock patient with different signature
        mock_patient = {
            'id': 1,
            'name': 'Test Patient',
            'signature': 'Dr Other',  # Different from session username
            'adresse': 'Test Address'
        }
        mock_db_connection.fetchone.return_value = mock_patient
        
        response = authenticated_session.get('/get_patient/1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'droit de modifier' in data['message']
    
    def test_doctor_can_access_unsigned_patient(self, authenticated_session, mock_db_connection):
        """Test doctor can access patient without signature"""
        # Mock patient with no signature
        mock_patient = {
            'id': 1,
            'name': 'Test Patient',
            'signature': None,
            'adresse': 'Test Address'
        }
        mock_db_connection.fetchone.return_value = mock_patient
        
        response = authenticated_session.get('/get_patient/1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['name'] == 'Test Patient'
    
    def test_nurse_can_access_patient_info(self, nurse_session, mock_db_connection):
        """Test nurses can access basic patient information"""
        mock_patient = {
            'id': 1,
            'name': 'Test Patient',
            'signature': 'Dr Other',  # Different doctor
            'adresse': 'Test Address'
        }
        mock_db_connection.fetchone.return_value = mock_patient
        
        response = nurse_session.get('/get_patient/1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['name'] == 'Test Patient'
    
    def test_receptionist_can_access_patient_info(self, receptionist_session, mock_db_connection):
        """Test receptionists can access basic patient information"""
        mock_patient = {
            'id': 1,
            'name': 'Test Patient',
            'signature': 'Dr Other',  # Different doctor
            'adresse': 'Test Address'
        }
        mock_db_connection.fetchone.return_value = mock_patient
        
        response = receptionist_session.get('/get_patient/1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['name'] == 'Test Patient'
    
    def test_special_doctor_access(self, client, mock_db_connection):
        """Test special doctor (Dr_Toralta_G_.Josephine) can access all patients"""
        with client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'Dr_Toralta_G_.Josephine'
            session['user_type'] = 'medecins'
        
        # Mock patient with different signature
        mock_patient = {
            'id': 1,
            'name': 'Test Patient',
            'signature': 'Dr Other',
            'adresse': 'Test Address'
        }
        mock_db_connection.fetchone.return_value = mock_patient
        
        response = client.get('/get_patient/1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['name'] == 'Test Patient'
    
    def test_unauthenticated_access_denied(self, client):
        """Test unauthenticated users cannot access protected routes"""
        protected_routes = [
            '/',
            '/search',
            '/get_patient/1',
            '/patient/1',
            '/add',
            '/update/1',
            '/delete/1',
            '/stat'
        ]
        
        for route in protected_routes:
            if route == '/add':
                response = client.post(route, json={'name': 'Test'})
            elif route == '/update/1':
                response = client.put(route, json={'name': 'Test'})
            elif route == '/delete/1':
                response = client.delete(route)
            else:
                response = client.get(route, follow_redirects=False)
            
            assert response.status_code == 302  # Redirect to login
            if hasattr(response, 'location'):
                assert '/login' in response.location
    
    @patch('app.CREDENTIALS', {'Dr_Toralta_G_.Josephine': 'admin_pass'})
    def test_admin_report_access(self, client, mock_db_connection):
        """Test only specific doctor can access daily reports"""
        with client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'Dr_Toralta_G_.Josephine'
            session['user_type'] = 'medecins'
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.readlines.return_value = ['Test log line']
            
            response = client.get('/report')
            assert response.status_code == 200
            assert b'rapport' in response.data.lower()
    
    def test_patient_signature_assignment(self, authenticated_session, mock_db_connection):
        """Test that patient gets doctor's signature when added by doctor"""
        patient_data = {
            'name': 'Test Patient',
            'adresse': 'Test Address'
        }
        
        mock_db_connection.execute.return_value = None
        
        response = authenticated_session.post('/add',
            data=json.dumps(patient_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # Verify that execute was called with signature
        mock_db_connection.execute.assert_called_once()
        call_args = mock_db_connection.execute.call_args
        query, values = call_args[0]
        
        # Check if signature is in the values
        signature_found = False
        if 'signature' in query:
            signature_found = True
        
        assert signature_found or 'Dr Test' in str(values)
