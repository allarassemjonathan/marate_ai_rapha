import pytest
from unittest.mock import patch, mock_open, MagicMock
import os
from datetime import datetime

class TestLogging:
    """Test logging functionality and activity tracking"""
    
    @patch('builtins.open', new_callable=mock_open, read_data='2024-01-01\nExisting log entry')
    @patch('os.path.exists')
    def test_log_file_append_same_date(self, mock_exists, mock_file):
        """Test logging appends to existing file with same date"""
        from app import log_file
        
        mock_exists.return_value = True
        
        with patch('app.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.side_effect = lambda fmt: {
                '%Y-%m-%d': '2024-01-01',
                '%H:%M:%S': '10:30:45'
            }[fmt]
            
            result = log_file('test_user', 'test_action', 'test_details')
            
            assert result == 200
            mock_file.assert_called()
            
            # Verify append mode was used
            append_call_found = False
            for call in mock_file.call_args_list:
                if 'a' in str(call):
                    append_call_found = True
                    break
            assert append_call_found
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_log_file_new_date(self, mock_exists, mock_file):
        """Test logging creates new file for new date"""
        from app import log_file
        
        mock_exists.return_value = False
        
        with patch('app.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.side_effect = lambda fmt: {
                '%Y-%m-%d': '2024-01-02',
                '%H:%M:%S': '10:30:45'
            }[fmt]
            
            result = log_file('test_user', 'test_action', 'test_details')
            
            assert result == 200
            mock_file.assert_called()
            
            # Verify write mode was used for new file
            write_call_found = False
            for call in mock_file.call_args_list:
                if 'w' in str(call):
                    write_call_found = True
                    break
            assert write_call_found
    
    @patch('builtins.open', new_callable=mock_open, read_data='2024-01-01\nOld entry')
    @patch('os.path.exists')
    def test_log_file_date_mismatch(self, mock_exists, mock_file):
        """Test logging overwrites file when date doesn't match"""
        from app import log_file
        
        mock_exists.return_value = True
        
        with patch('app.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.side_effect = lambda fmt: {
                '%Y-%m-%d': '2024-01-02',  # Different date
                '%H:%M:%S': '10:30:45'
            }[fmt]
            
            result = log_file('test_user', 'test_action', 'test_details')
            
            assert result == 200
            
            # Should overwrite file with new date
            write_calls = [call for call in mock_file.call_args_list if 'w' in str(call)]
            assert len(write_calls) > 0
    
    def test_log_file_content_format(self, mock_db_connection):
        """Test that log file content is formatted correctly"""
        from app import log_file
        
        with patch('builtins.open', new_callable=mock_open) as mock_file:
            with patch('os.path.exists', return_value=False):
                with patch('app.datetime') as mock_datetime:
                    mock_datetime.now.return_value.strftime.side_effect = lambda fmt: {
                        '%Y-%m-%d': '2024-01-01',
                        '%H:%M:%S': '15:30:45'
                    }[fmt]
                    
                    log_file('doctor', 'patient_added', 'Patient John Doe added')
                    
                    # Get the written content
                    handle = mock_file.return_value.__enter__.return_value
                    write_calls = [call[0][0] for call in handle.write.call_args_list]
                    
                    # Check date header
                    assert '2024-01-01' in write_calls[0]
                    
                    # Check log entry format
                    log_entry = write_calls[1] if len(write_calls) > 1 else write_calls[0]
                    assert 'Nouvelle evenement: 15:30:45 doctor, patient_added, Patient John Doe added' in log_entry
    
    def test_log_file_encoding(self):
        """Test that log file uses correct encoding"""
        from app import log_file
        
        with patch('builtins.open', new_callable=mock_open) as mock_file:
            with patch('os.path.exists', return_value=False):
                
                log_file('test_user', 'test_action', 'test_details')
                
                # Verify latin-1 encoding is used
                for call in mock_file.call_args_list:
                    if 'encoding' in call.kwargs:
                        assert call.kwargs['encoding'] == 'latin-1'
    
    def test_logging_with_special_characters(self):
        """Test logging handles special characters correctly"""
        from app import log_file
        
        with patch('builtins.open', new_callable=mock_open) as mock_file:
            with patch('os.path.exists', return_value=False):
                
                # Test with special characters that might cause encoding issues
                result = log_file('médecin', 'ajout_patient', 'Patienté ajouté avec succès')
                
                assert result == 200
                mock_file.assert_called()
    
    def test_login_logout_logging(self, client, mock_db_connection):
        """Test that login/logout actions are properly logged"""
        
        with patch('app.log_file') as mock_log:
            with patch('app.CREDENTIALS', {'test_user': 'test_pass'}):
                
                # Test login logging
                response = client.post('/login', data={
                    'username': 'test_user',
                    'password': 'test_pass'
                })
                
                # Should log successful login
                login_logged = False
                for call in mock_log.call_args_list:
                    if 'login' in str(call):
                        login_logged = True
                        break
                assert login_logged
                
                mock_log.reset_mock()
                
                # Test logout logging
                with client.session_transaction() as session:
                    session['logged_in'] = True
                    session['user_type'] = 'test_user'
                
                response = client.get('/logout')
                
                # Should log logout
                logout_logged = False
                for call in mock_log.call_args_list:
                    if 'logout' in str(call):
                        logout_logged = True
                        break
                assert logout_logged
    
    def test_patient_operations_logging(self, authenticated_session, mock_db_connection):
        """Test that patient operations are logged"""
        
        with patch('app.log_file') as mock_log:
            
            # Test patient addition logging
            patient_data = {'name': 'Test Patient', 'adresse': 'Test Address'}
            
            response = authenticated_session.post('/add',
                data=json.dumps(patient_data),
                content_type='application/json'
            )
            
            # Should log patient addition
            add_logged = False
            for call in mock_log.call_args_list:
                if "Ajout d'un patient" in str(call) or 'patient_added' in str(call):
                    add_logged = True
                    break
            assert add_logged
            
            mock_log.reset_mock()
            
            # Test patient update logging
            update_data = {'name': 'Updated Patient', 'adresse': 'Updated Address'}
            
            response = authenticated_session.put('/update/1',
                data=json.dumps(update_data),
                content_type='application/json'
            )
            
            # Should log patient update
            update_logged = False
            for call in mock_log.call_args_list:
                if 'modification patient' in str(call) or 'patient_updated' in str(call):
                    update_logged = True
                    break
            assert update_logged
            
            mock_log.reset_mock()
            
            # Test patient deletion logging
            mock_db_connection.fetchall.return_value = [{'id': 1, 'name': 'Test Patient'}]
            
            response = authenticated_session.delete('/delete/1')
            
            # Should log patient deletion
            delete_logged = False
            for call in mock_log.call_args_list:
                if "Suppression d'un patient" in str(call) or 'patient_deleted' in str(call):
                    delete_logged = True
                    break
            assert delete_logged
    
    def test_invoice_generation_logging(self, authenticated_session, mock_db_connection):
        """Test that invoice generation is logged"""
        
        invoice_data = {
            'meta': {
                'nom': 'Doe',
                'prenom': 'John',
                'pourcentage': '80'
            },
            'sections': [{
                'titre': 'Test',
                'articles': [{'libelle': 'Test', 'quantite': 1, 'montant': 100}]
            }]
        }
        
        with patch('app.log_file') as mock_log:
            with patch('app.InvoicePDF'):
                with patch('tempfile.NamedTemporaryFile') as mock_temp:
                    mock_temp.return_value.__enter__.return_value.name = 'test.pdf'
                    
                    response = authenticated_session.post('/generate_invoice/1',
                        data=json.dumps(invoice_data),
                        content_type='application/json'
                    )
                    
                    # Should log invoice generation
                    invoice_logged = False
                    for call in mock_log.call_args_list:
                        if 'Facture généré' in str(call) or 'invoice_generated' in str(call):
                            invoice_logged = True
                            break
                    assert invoice_logged

import json
