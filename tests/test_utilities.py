import pytest
from unittest.mock import patch, MagicMock
from app import clean_float, init_db
import psycopg2

class TestUtilityFunctions:
    """Test utility functions and helper methods"""
    
    def test_clean_float_valid_number(self):
        """Test clean_float with valid number string"""
        assert clean_float("123.45") == 123.45
        assert clean_float("0") == 0.0
        assert clean_float("42") == 42.0
    
    def test_clean_float_empty_string(self):
        """Test clean_float with empty string"""
        assert clean_float("") is None
        assert clean_float("   ") is None
    
    def test_clean_float_whitespace(self):
        """Test clean_float with whitespace"""
        assert clean_float("  123.45  ") == 123.45
        assert clean_float("\t456.78\n") == 456.78
    
    def test_clean_float_invalid_input(self):
        """Test clean_float with invalid input"""
        with pytest.raises(ValueError):
            clean_float("not_a_number")
        
        with pytest.raises(ValueError):
            clean_float("12.34.56")

class TestDatabaseOperations:
    """Test database initialization and operations"""
    
    @patch('app.get_db_connection')
    def test_init_db_success(self, mock_get_connection):
        """Test successful database initialization"""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        
        mock_get_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        # This should not raise an exception
        init_db()
        
        # Verify that execute was called for table creation
        assert mock_cursor.execute.call_count >= 3  # patients, visits, action_logs tables
        mock_connection.commit.assert_called_once()
    
    @patch('app.get_db_connection')
    def test_init_db_connection_error(self, mock_get_connection):
        """Test database initialization with connection error"""
        mock_get_connection.side_effect = psycopg2.Error("Connection failed")
        
        # Should raise the database error
        with pytest.raises(psycopg2.Error):
            init_db()
    
    @patch('app.get_db_connection')
    def test_database_table_creation_queries(self, mock_get_connection):
        """Test that correct table creation queries are executed"""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        
        mock_get_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        init_db()
        
        # Get all execute calls
        execute_calls = mock_cursor.execute.call_args_list
        
        # Verify table creation queries
        patients_table_created = False
        visits_table_created = False
        logs_table_created = False
        
        for call in execute_calls:
            query = call[0][0].upper()
            if 'CREATE TABLE' in query and 'PATIENTS' in query:
                patients_table_created = True
                # Check for important columns
                assert 'NAME' in query
                assert 'SERIAL PRIMARY KEY' in query
            elif 'CREATE TABLE' in query and 'VISITS' in query:
                visits_table_created = True
            elif 'CREATE TABLE' in query and 'ACTION_LOGS' in query:
                logs_table_created = True
        
        assert patients_table_created
        assert visits_table_created
        assert logs_table_created

class TestDataValidation:
    """Test data validation and sanitization"""
    
    def test_patient_age_validation(self, authenticated_session):
        """Test patient age validation in add endpoint"""
        # Test valid age
        valid_patient = {
            'name': 'Test Patient',
            'age': 25
        }
        
        with patch('app.get_db_connection'):
            response = authenticated_session.post('/add',
                data=json.dumps(valid_patient),
                content_type='application/json'
            )
            assert response.status_code == 200
    
    def test_patient_weight_validation(self, authenticated_session):
        """Test patient weight validation"""
        # Test valid weight
        valid_patient = {
            'name': 'Test Patient',
            'poids': 70.5
        }
        
        with patch('app.get_db_connection'):
            response = authenticated_session.post('/add',
                data=json.dumps(valid_patient),
                content_type='application/json'
            )
            assert response.status_code == 200
    
    def test_empty_string_to_none_conversion(self, authenticated_session, mock_db_connection):
        """Test that empty strings are converted to None for database"""
        patient_data = {
            'name': 'Test Patient',
            'adresse': '',  # Empty string should become None
            'age': '',      # Empty string should become None
            'poids': '70.5'  # Valid number
        }
        
        response = authenticated_session.post('/add',
            data=json.dumps(patient_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # Verify that execute was called with None for empty fields
        mock_db_connection.execute.assert_called_once()
        call_args = mock_db_connection.execute.call_args
        values = call_args[0][1]  # Second argument contains the values
        
        # Check that empty strings became None
        # The exact position depends on the field order, but None should be present
        assert None in values

class TestErrorHandling:
    """Test error handling throughout the application"""
    
    def test_database_error_handling(self, authenticated_session):
        """Test that database errors are handled gracefully"""
        patient_data = {'name': 'Test Patient'}
        
        with patch('app.get_db_connection') as mock_conn:
            mock_conn.side_effect = psycopg2.Error("Database connection failed")
            
            response = authenticated_session.post('/add',
                data=json.dumps(patient_data),
                content_type='application/json'
            )
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['status'] == 'error'
    
    def test_invalid_json_handling(self, authenticated_session):
        """Test handling of invalid JSON in requests"""
        response = authenticated_session.post('/add',
            data='invalid json data',
            content_type='application/json'
        )
        
        # Should handle invalid JSON gracefully
        assert response.status_code in [400, 500]
    
    def test_missing_patient_id_handling(self, authenticated_session, mock_db_connection):
        """Test handling of requests for non-existent patients"""
        mock_db_connection.fetchone.return_value = None
        
        response = authenticated_session.get('/get_patient/99999')
        
        # Should handle missing patient gracefully
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data is None or 'error' in data.get('status', '')

class TestSessionManagement:
    """Test session handling and security"""
    
    def test_session_security(self, client):
        """Test that session data is properly secured"""
        with client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'test_user'
            session['user_type'] = 'medecins'
        
        # Session should persist
        response = client.get('/')
        assert response.status_code == 200
    
    def test_session_cleanup_on_logout(self, client):
        """Test that session is properly cleaned up on logout"""
        # Set up session
        with client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'test_user'
            session['user_type'] = 'medecins'
            session['extra_data'] = 'should_be_cleared'
        
        # Logout
        response = client.get('/logout')
        assert response.status_code == 302
        
        # Check that session was cleared
        with client.session_transaction() as session:
            assert not session.get('logged_in')
            assert not session.get('username')
            assert not session.get('user_type')
            assert not session.get('extra_data')
    
    def test_session_required_fields(self, client):
        """Test that both logged_in and username are required"""
        # Test with only logged_in
        with client.session_transaction() as session:
            session['logged_in'] = True
        
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302
        
        # Test with only username
        with client.session_transaction() as session:
            session.clear()
            session['username'] = 'test_user'
        
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302

import json
