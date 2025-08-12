import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from app import app, init_db

@pytest.fixture
def client():
    """Create a test client"""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    with app.test_client() as client:
        with app.app_context():
            yield client

@pytest.fixture
def mock_db_connection():
    """Mock database connections"""
    with patch('app.get_db_connection') as mock_conn:
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        
        # Set up the context manager behavior for connection
        mock_conn.return_value.__enter__.return_value = mock_connection
        mock_conn.return_value.__exit__.return_value = None
        
        # Set up the context manager behavior for cursor
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connection.cursor.return_value.__exit__.return_value = None
        
        yield mock_cursor

@pytest.fixture
def authenticated_session(client):
    """Create an authenticated session for doctors"""
    with client.session_transaction() as session:
        session['logged_in'] = True
        session['username'] = 'Dr_Test'
        session['user_type'] = 'medecins'
    return client

@pytest.fixture
def nurse_session(client):
    """Create an authenticated session for nurses"""
    with client.session_transaction() as session:
        session['logged_in'] = True
        session['username'] = 'infirmiers'
        session['user_type'] = 'infirmiers'
    return client

@pytest.fixture
def receptionist_session(client):
    """Create an authenticated session for receptionists"""
    with client.session_transaction() as session:
        session['logged_in'] = True
        session['username'] = 'receptionistes'
        session['user_type'] = 'receptionistes'
    return client
