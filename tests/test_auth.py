import pytest
from unittest.mock import patch, MagicMock
import json

class TestAuthentication:
    """Test authentication and authorization functionality"""
    
    def test_login_page_accessible(self, client):
        """Test that login page is accessible"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    @patch('app.CREDENTIALS', {'test_user': 'test_pass'})
    def test_login_success(self, client):
        """Test successful login"""
        response = client.post('/login', data={
            'username': 'test_user',
            'password': 'test_pass'
        }, follow_redirects=False)
        assert response.status_code == 302  # Redirect after login
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post('/login', data={
            'username': 'invalid_user',
            'password': 'wrong_password'
        })
        assert response.status_code == 200
        assert b'incorrects' in response.data or b'error' in response.data.lower()
    
    def test_login_empty_credentials(self, client):
        """Test login with empty credentials"""
        response = client.post('/login', data={
            'username': '',
            'password': ''
        })
        assert response.status_code == 200
        # Should remain on login page
    
    def test_logout_functionality(self, authenticated_session):
        """Test logout clears session"""
        response = authenticated_session.get('/logout')
        assert response.status_code == 302  # Redirect to login
        
        # Try to access protected route after logout
        response = authenticated_session.get('/', follow_redirects=False)
        assert response.status_code == 302  # Should redirect to login
    
    def test_login_required_decorator(self, client):
        """Test that protected routes redirect to login"""
        protected_routes = ['/', '/search', '/add']
        
        for route in protected_routes:
            response = client.get(route, follow_redirects=False)
            assert response.status_code == 302
            assert '/login' in response.location
    
    @patch('app.CREDENTIALS', {
        'Dr_Test_Doctor': 'doctor_pass',
        'infirmiers': 'nurse_pass',
        'receptionistes': 'reception_pass'
    })
    def test_user_type_assignment(self, client):
        """Test that user types are correctly assigned"""
        # Test doctor login
        with client.session_transaction() as session:
            session.clear()
        
        response = client.post('/login', data={
            'username': 'Dr_Test_Doctor',
            'password': 'doctor_pass'
        }, follow_redirects=False)
        
        if response.status_code == 302:
            with client.session_transaction() as session:
                assert session.get('user_type') == 'medecins'
    
    def test_session_persistence(self, authenticated_session):
        """Test that session persists across requests"""
        # First request
        response1 = authenticated_session.get('/')
        assert response1.status_code == 200
        
        # Second request should still be authenticated
        response2 = authenticated_session.get('/')
        assert response2.status_code == 200
