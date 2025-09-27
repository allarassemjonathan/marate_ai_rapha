import pytest
from unittest.mock import patch, MagicMock
import smtplib
from email.mime.multipart import MIMEMultipart

class TestEmailFunctionality:
    """Test email notification system"""
    
    @patch('app.smtplib.SMTP')
    def test_email_reception_success(self, mock_smtp):
        """Test successful email sending"""
        from app import email_reception
        
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        result = email_reception(
            'John', 'Doe', 'Test email body', None, 'test@example.com'
        )
        
        # Verify SMTP operations
        mock_smtp.assert_called_once_with('smtp.gmail.com', 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()
    
    @patch('app.smtplib.SMTP')
    def test_email_reception_with_attachment(self, mock_smtp):
        """Test email sending with attachment"""
        from app import email_reception
        
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        # Mock plot attachment
        mock_plot = MagicMock()
        mock_plot.getvalue.return_value = b'fake_plot_data'
        
        result = email_reception(
            'John', 'Doe', 'Test email body', mock_plot, 'test@example.com'
        )
        
        # Verify SMTP operations
        mock_server.send_message.assert_called_once()
        
        # Verify that plot data was accessed
        mock_plot.getvalue.assert_called_once()
    
    @patch('app.smtplib.SMTP')
    def test_email_reception_smtp_error(self, mock_smtp):
        """Test email sending with SMTP error"""
        from app import email_reception
        
        # Mock SMTP error
        mock_smtp.side_effect = smtplib.SMTPException("SMTP Error")
        
        # Should not raise exception, but handle it gracefully
        result = email_reception(
            'John', 'Doe', 'Test email body', None, 'test@example.com'
        )
        
        # Function should complete without raising exception
        assert result is not None
    
    @patch('app.smtplib.SMTP')
    def test_email_reception_connection_error(self, mock_smtp):
        """Test email sending with connection error"""
        from app import email_reception
        
        # Mock connection error
        mock_smtp.side_effect = ConnectionError("Connection failed")
        
        # Should handle gracefully
        result = email_reception(
            'John', 'Doe', 'Test email body', None, 'test@example.com'
        )
        
        assert result is not None
    
    @patch('app.smtplib.SMTP')
    def test_email_subject_formatting(self, mock_smtp):
        """Test that email subject is formatted correctly"""
        from app import email_reception
        
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        email_reception('John', 'Doe', 'Test body', None, 'test@example.com')
        
        # Get the message that was sent
        call_args = mock_server.send_message.call_args[0]
        message = call_args[0]
        
        # Check subject formatting
        assert message['Subject'] == 'Nouveau patient John Doe'
    
    @patch('app.smtplib.SMTP')
    def test_email_html_content(self, mock_smtp):
        """Test that email contains HTML content with logo"""
        from app import email_reception
        
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        test_body = "This is a test email body"
        email_reception('John', 'Doe', test_body, None, 'test@example.com')
        
        # Get the message that was sent
        call_args = mock_server.send_message.call_args[0]
        message = call_args[0]
        
        # Check that message has parts (HTML content)
        assert len(message.get_payload()) > 0
        
        # Check that HTML content includes the test body
        html_part = None
        for part in message.walk():
            if part.get_content_type() == 'text/html':
                html_part = part.get_payload()
                break
        
        assert html_part is not None
        assert test_body in html_part
        assert 'marate_white.png' in html_part  # Logo URL should be in HTML
    
    @patch('app.smtplib.SMTP')
    def test_email_environment_variables(self, mock_smtp):
        """Test that email uses environment variables correctly"""
        from app import email_reception
        
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        with patch('app.smtp_server', 'test.smtp.com'):
            with patch('app.smtp_port', 555):
                with patch('app.your_email', 'test@test.com'):
                    with patch('app.your_password', 'testpass'):
                        
                        email_reception('John', 'Doe', 'Test', None, 'recipient@test.com')
                        
                        # Verify SMTP was called with correct server and port
                        mock_smtp.assert_called_once_with('test.smtp.com', 555)
                        
                        # Verify login was called with correct credentials
                        mock_server.login.assert_called_once_with('test@test.com', 'testpass')
    
    def test_email_message_structure(self):
        """Test email message structure creation"""
        from app import email_reception
        
        with patch('app.smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_reception('John', 'Doe', 'Test body', None, 'test@example.com')
            
            # Get the message
            call_args = mock_server.send_message.call_args[0]
            message = call_args[0]
            
            # Verify message structure
            assert isinstance(message, MIMEMultipart)
            assert message['Subject'] is not None
            assert message['From'] is not None
            assert message['To'] == 'test@example.com'
    
    @patch('builtins.open', create=True)
    @patch('app.smtplib.SMTP')
    def test_daily_report_email(self, mock_smtp, mock_open):
        """Test daily report email functionality"""
        from app import app
        
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        # Mock file reading
        mock_open.return_value.__enter__.return_value.readlines.return_value = [
            'Test log line 1\n',
            'Test log line 2\n'
        ]
        
        with app.test_client() as client:
            with client.session_transaction() as session:
                session['logged_in'] = True
                session['username'] = 'Dr_Toralta_G_.Josephine'
                session['user_type'] = 'medecins'
            
            response = client.get('/report')
            assert response.status_code == 200
            
            # Verify email was sent
            mock_server.send_message.assert_called_once()
            
            # Get the message
            call_args = mock_server.send_message.call_args[0]
            message = call_args[0]
            
            # Verify it's a daily report
            assert 'Daily Action Report' in message['Subject']
            assert message['To'] == 'Josephinetoralta@gmail.com'
