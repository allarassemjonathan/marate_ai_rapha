import pytest
from unittest.mock import patch, MagicMock
import json

class TestIntegration:
    """Integration tests for complete user workflows"""
    
    def test_complete_patient_workflow(self, authenticated_session, mock_db_connection):
        """Test complete patient management workflow"""
        # Step 1: Add a new patient
        patient_data = {
            'name': 'John Doe',
            'adresse': '123 Main St',
            'age': 30,
            'poids': 70.5
        }
        
        with patch('app.email_reception'):  # Mock email sending
            response = authenticated_session.post('/add',
                data=json.dumps(patient_data),
                content_type='application/json'
            )
            assert response.status_code == 200
        
        # Step 2: Search for the patient
        mock_db_connection.fetchall.return_value = [
            {'id': 1, 'name': 'John Doe', 'adresse': '123 Main St', 'age': 30}
        ]
        
        response = authenticated_session.get('/search?q=John')
        assert response.status_code == 200
        patients = json.loads(response.data)
        assert len(patients) == 1
        assert patients[0]['name'] == 'John Doe'
        
        # Step 3: Get patient details
        mock_db_connection.fetchone.return_value = {
            'id': 1, 'name': 'John Doe', 'signature': 'Dr Test'
        }
        
        response = authenticated_session.get('/get_patient/1')
        assert response.status_code == 200
        patient = json.loads(response.data)
        assert patient['name'] == 'John Doe'
        
        # Step 4: Update patient information
        update_data = {
            'name': 'John Doe',
            'adresse': '456 Oak St',
            'temperature': 37.2
        }
        
        with patch('app.email_reception'):  # Mock email for temperature update
            response = authenticated_session.put('/update/1',
                data=json.dumps(update_data),
                content_type='application/json'
            )
            assert response.status_code == 200
        
        # Step 5: Generate invoice
        invoice_data = {
            'meta': {
                'nom': 'Doe',
                'prenom': 'John',
                'pourcentage': '80'
            },
            'sections': [{
                'titre': 'Consultation',
                'articles': [{
                    'libelle': 'Examen général',
                    'quantite': 1,
                    'montant': 5000
                }]
            }]
        }
        
        with patch('app.InvoicePDF'):
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = 'test.pdf'
                
                response = authenticated_session.post('/generate_invoice/1',
                    data=json.dumps(invoice_data),
                    content_type='application/json'
                )
                assert response.status_code == 200
        
        # Step 6: Delete patient
        mock_db_connection.fetchall.return_value = [{'id': 1, 'name': 'John Doe'}]
        
        response = authenticated_session.delete('/delete/1')
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['status'] == 'deleted'
    
    def test_multi_user_workflow(self, client, mock_db_connection):
        """Test workflow with different user types"""
        # Receptionist adds patient
        with client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'receptionistes'
            session['user_type'] = 'receptionistes'
        
        patient_data = {
            'name': 'Jane Smith',
            'adresse': '789 Pine St',
            'phone_number': '123-456-7890'
        }
        
        with patch('app.email_reception'):
            response = client.post('/add',
                data=json.dumps(patient_data),
                content_type='application/json'
            )
            assert response.status_code == 200
        
        # Nurse updates vital signs
        with client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'infirmiers'
            session['user_type'] = 'infirmiers'
        
        mock_db_connection.fetchone.return_value = {
            'id': 1, 'name': 'Jane Smith', 'signature': None
        }
        
        response = client.get('/get_patient/1')
        assert response.status_code == 200
        
        vital_signs = {
            'name': 'Jane Smith',
            'temperature': 36.8,
            'poids': 65.0,
            'taille': 165.0,
            'tension_arterielle': '120/80'
        }
        
        with patch('app.email_reception'):
            response = client.put('/update/1',
                data=json.dumps(vital_signs),
                content_type='application/json'
            )
            assert response.status_code == 200
        
        # Doctor completes diagnosis
        with client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'Dr_Test'
            session['user_type'] = 'medecins'
        
        mock_db_connection.fetchone.return_value = {
            'id': 1, 'name': 'Jane Smith', 'signature': 'Dr Test'
        }
        
        diagnosis_data = {
            'name': 'Jane Smith',
            'hypothese_de_diagnostique': 'Routine checkup',
            'ordonnance': 'Continue current medication'
        }
        
        response = client.put('/update/1',
            data=json.dumps(diagnosis_data),
            content_type='application/json'
        )
        assert response.status_code == 200
    
    def test_error_recovery_workflow(self, authenticated_session, mock_db_connection):
        """Test that system recovers gracefully from errors"""
        # Attempt to add patient with invalid data
        invalid_patient = {
            'name': '',  # Invalid: empty name
            'age': 'not_a_number'  # Invalid: non-numeric age
        }
        
        response = authenticated_session.post('/add',
            data=json.dumps(invalid_patient),
            content_type='application/json'
        )
        assert response.status_code == 400
        
        # System should still work after error
        valid_patient = {
            'name': 'Valid Patient',
            'age': 25
        }
        
        with patch('app.email_reception'):
            response = authenticated_session.post('/add',
                data=json.dumps(valid_patient),
                content_type='application/json'
            )
            assert response.status_code == 200
    
    def test_concurrent_user_simulation(self, client, mock_db_connection):
        """Simulate multiple users accessing the system"""
        # Simulate concurrent requests from different users
        users = [
            {'username': 'Dr_Test', 'user_type': 'medecins'},
            {'username': 'infirmiers', 'user_type': 'infirmiers'},
            {'username': 'receptionistes', 'user_type': 'receptionistes'}
        ]
        
        for user in users:
            with client.session_transaction() as session:
                session['logged_in'] = True
                session['username'] = user['username']
                session['user_type'] = user['user_type']
            
            # Each user searches for patients
            mock_db_connection.fetchall.return_value = [
                {'id': 1, 'name': 'Patient 1'},
                {'id': 2, 'name': 'Patient 2'}
            ]
            
            response = client.get('/search?q=Patient')
            assert response.status_code == 200
            
            # Each user accesses main page
            response = client.get('/')
            assert response.status_code == 200
    
    def test_data_consistency_workflow(self, authenticated_session, mock_db_connection):
        """Test data consistency across operations"""
        # Add patient
        patient_data = {
            'name': 'Consistency Test',
            'age': 40,
            'adresse': 'Test Address'
        }
        
        with patch('app.email_reception'):
            response = authenticated_session.post('/add',
                data=json.dumps(patient_data),
                content_type='application/json'
            )
            assert response.status_code == 200
        
        # Verify data is retrievable
        mock_db_connection.fetchone.return_value = {
            'id': 1,
            'name': 'Consistency Test',
            'age': 40,
            'adresse': 'Test Address',
            'signature': 'Dr Test'
        }
        
        response = authenticated_session.get('/get_patient/1')
        assert response.status_code == 200
        
        patient = json.loads(response.data)
        assert patient['name'] == patient_data['name']
        assert patient['age'] == patient_data['age']
        assert patient['adresse'] == patient_data['adresse']
        
        # Update and verify consistency
        update_data = {
            'name': 'Consistency Test',
            'age': 41,  # Updated age
            'adresse': 'Updated Address'
        }
        
        response = authenticated_session.put('/update/1',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        assert response.status_code == 200
    
    def test_logging_integration(self, authenticated_session, mock_db_connection):
        """Test that all operations are properly logged"""
        with patch('app.log_file') as mock_log:
            
            # Add patient - should be logged
            patient_data = {'name': 'Log Test Patient'}
            
            with patch('app.email_reception'):
                response = authenticated_session.post('/add',
                    data=json.dumps(patient_data),
                    content_type='application/json'
                )
                assert response.status_code == 200
            
            # Update patient - should be logged
            mock_db_connection.fetchone.return_value = {
                'id': 1, 'signature': 'Dr Test'
            }
            
            response = authenticated_session.put('/update/1',
                data=json.dumps({'name': 'Updated Patient'}),
                content_type='application/json'
            )
            assert response.status_code == 200
            
            # Generate invoice - should be logged
            invoice_data = {
                'meta': {'nom': 'Test', 'prenom': 'User', 'pourcentage': '80'},
                'sections': [{
                    'titre': 'Test',
                    'articles': [{'libelle': 'Test', 'quantite': 1, 'montant': 100}]
                }]
            }
            
            with patch('app.InvoicePDF'):
                with patch('tempfile.NamedTemporaryFile') as mock_temp:
                    mock_temp.return_value.__enter__.return_value.name = 'test.pdf'
                    
                    response = authenticated_session.post('/generate_invoice/1',
                        data=json.dumps(invoice_data),
                        content_type='application/json'
                    )
                    assert response.status_code == 200
            
            # Verify all operations were logged
            assert mock_log.call_count >= 3  # Add, update, and invoice generation
