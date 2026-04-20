import pytest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime

class TestPatientManagement:
    """Test patient CRUD operations"""
    
    def test_add_patient_success(self, authenticated_session, mock_db_connection):
        """Test successfully adding a new patient"""
        patient_data = {
            'name': 'Test Patient',
            'adresse': 'Test Address',
            'age': 30,
            'poids': 70.5,
            'taille': 175.0,
            'phone_number': '123456789'
        }
        
        mock_db_connection.execute.return_value = None
        
        response = authenticated_session.post('/add',
            data=json.dumps(patient_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        mock_db_connection.execute.assert_called_once()
    
    def test_add_patient_missing_name(self, authenticated_session):
        """Test adding patient without required name"""
        patient_data = {
            'adresse': 'Test Address',
            'age': 30
        }
        
        response = authenticated_session.post('/add',
            data=json.dumps(patient_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'Name is required' in data['message']
    
    def test_add_patient_invalid_age(self, authenticated_session):
        """Test adding patient with invalid age"""
        patient_data = {
            'name': 'Test Patient',
            'age': 'invalid_age'
        }
        
        response = authenticated_session.post('/add',
            data=json.dumps(patient_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'must be a number' in data['message']
    
    def test_search_patients(self, authenticated_session, mock_db_connection):
        """Test patient search functionality"""
        mock_db_connection.fetchall.return_value = [
            {'id': 1, 'name': 'John Doe', 'adresse': 'Test St', 'age': 25},
            {'id': 2, 'name': 'Jane Doe', 'adresse': 'Main St', 'age': 30}
        ]
        
        response = authenticated_session.get('/search?q=Doe')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2
        assert data[0]['name'] == 'John Doe'
        assert data[1]['name'] == 'Jane Doe'
    
    def test_search_patients_empty_query(self, authenticated_session, mock_db_connection):
        """Test patient search with empty query"""
        mock_db_connection.fetchall.return_value = []
        
        response = authenticated_session.get('/search?q=')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_update_patient_success(self, authenticated_session, mock_db_connection):
        """Test successfully updating patient information"""
        update_data = {
            'name': 'Updated Name',
            'age': 35,
            'adresse': 'Updated Address'
        }
        
        mock_db_connection.execute.return_value = None
        
        response = authenticated_session.put('/update/1',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        mock_db_connection.execute.assert_called_once()
    
    def test_update_patient_missing_name(self, authenticated_session):
        """Test updating patient without required name"""
        update_data = {
            'age': 35,
            'adresse': 'Updated Address'
        }
        
        response = authenticated_session.put('/update/1',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'Name is required' in data['message']
    
    def test_delete_patient(self, authenticated_session, mock_db_connection):
        """Test deleting a patient"""
        mock_db_connection.fetchall.return_value = [
            {'id': 1, 'name': 'Test Patient', 'adresse': 'Test Address'}
        ]
        
        response = authenticated_session.delete('/delete/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'deleted'
        
        # Verify delete was called
        assert mock_db_connection.execute.call_count >= 1
    
    def test_get_patient_success(self, authenticated_session, mock_db_connection):
        """Test getting patient information"""
        mock_patient = {
            'id': 1,
            'name': 'Test Patient',
            'signature': 'Dr Test',  # Match session username
            'adresse': 'Test Address',
            'age': 30
        }
        mock_db_connection.fetchone.return_value = mock_patient
        
        response = authenticated_session.get('/get_patient/1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['name'] == 'Test Patient'
        assert data['id'] == 1
    
    def test_patient_detail_page(self, authenticated_session, mock_db_connection):
        """Test patient detail page rendering"""
        # Mock patient data
        mock_patient = [{'id': 1, 'name': 'Test Patient', 'adresse': 'Test St'}]
        mock_visits = [
            {'id': 1, 'name': 'Test Patient', 'visit_date': '2024-01-01', 'notes': 'Test visit'}
        ]
        
        mock_db_connection.fetchall.side_effect = [mock_patient, mock_visits]
        
        response = authenticated_session.get('/patient/1')
        assert response.status_code == 200
        assert b'Test Patient' in response.data
    
    @patch('app.load_df')
    def test_statistics_endpoint(self, mock_load_df, authenticated_session, mock_db_connection):
        """Test statistics page loads with Chart.js charts"""
        import pandas as pd
        mock_df = pd.DataFrame({
            'name': ['Patient A', 'Patient B', 'Patient A', 'Patient C'],
            'created_at': pd.to_datetime(['2025-01-10', '2025-01-15', '2025-02-10', '2025-02-20']),
            'adresse': ['Quartier1/Apt1', 'Quartier2/Apt2', 'Quartier1/Apt3', 'Quartier3/Apt4'],
            'new_cases': ['oui', 'oui', 'non', 'oui'],
            'signature': ['Dr Test', 'Dr Test', 'Dr Other', 'Dr Test']
        })
        mock_load_df.return_value = mock_df

        response = authenticated_session.get('/stat')
        assert response.status_code == 200
        # Verify Chart.js is loaded and data is injected
        assert b'chart.js' in response.data or b'chart.umd.min.js' in response.data
        assert b'CHART_DATA' in response.data
        assert b'chartDailyRevenue' in response.data
        assert b'chartMonthlyRevenue' in response.data
        assert b'chartEvolution' in response.data
        # Verify no matplotlib base64 images
        assert b'data:image/png;base64' not in response.data
