import pytest
from unittest.mock import patch, MagicMock
import json
import tempfile
from io import BytesIO

class TestPDFGeneration:
    """Test PDF invoice generation functionality"""
    
    def test_generate_invoice_success(self, authenticated_session, mock_db_connection):
        """Test successful PDF invoice generation"""
        invoice_data = {
            'meta': {
                'nom': 'Doe',
                'prenom': 'John',
                'pourcentage': '80',
                'assurance': 'Test Insurance',
                'police': '12345'
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
        
        with patch('app.InvoicePDF') as mock_pdf_class:
            mock_pdf = MagicMock()
            mock_pdf_class.return_value = mock_pdf
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = 'test.pdf'
                
                response = authenticated_session.post('/generate_invoice/1',
                    data=json.dumps(invoice_data),
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                mock_pdf.add_page.assert_called_once()
                mock_pdf.output.assert_called_once()
    
    def test_generate_invoice_missing_meta(self, authenticated_session):
        """Test PDF generation with missing metadata"""
        incomplete_data = {
            'sections': [{
                'titre': 'Test',
                'articles': [{'libelle': 'Test', 'quantite': 1, 'montant': 100}]
            }]
        }
        
        response = authenticated_session.post('/generate_invoice/1',
            data=json.dumps(incomplete_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'Metadata and sections are required' in data['message']
    
    def test_generate_invoice_missing_sections(self, authenticated_session):
        """Test PDF generation with missing sections"""
        incomplete_data = {
            'meta': {
                'nom': 'Doe',
                'prenom': 'John',
                'pourcentage': '80'
            }
        }
        
        response = authenticated_session.post('/generate_invoice/1',
            data=json.dumps(incomplete_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_generate_invoice_empty_request(self, authenticated_session):
        """Test PDF generation with empty request"""
        response = authenticated_session.post('/generate_invoice/1',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_generate_invoice_invalid_json(self, authenticated_session):
        """Test PDF generation with invalid JSON"""
        response = authenticated_session.post('/generate_invoice/1',
            data='invalid json',
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    @patch('app.InvoicePDF')
    def test_invoice_pdf_class_creation(self, mock_pdf_class, authenticated_session):
        """Test InvoicePDF class instantiation and methods"""
        invoice_data = {
            'meta': {
                'nom': 'Test',
                'prenom': 'User',
                'pourcentage': '80'
            },
            'sections': [{
                'titre': 'Test Section',
                'articles': [{
                    'libelle': 'Test Item',
                    'quantite': 1,
                    'montant': 1000
                }]
            }]
        }
        
        mock_pdf = MagicMock()
        mock_pdf_class.return_value = mock_pdf
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = 'test.pdf'
            
            response = authenticated_session.post('/generate_invoice/1',
                data=json.dumps(invoice_data),
                content_type='application/json'
            )
            
            # Verify PDF class was instantiated
            mock_pdf_class.assert_called_once()
            
            # Verify PDF methods were called
            mock_pdf.add_page.assert_called_once()
            mock_pdf.add_invoice_header.assert_called_once()
            mock_pdf.add_invoice_sections.assert_called_once()
            mock_pdf.output.assert_called_once()
    
    def test_invoice_calculations(self, authenticated_session):
        """Test that invoice calculations are correct"""
        invoice_data = {
            'meta': {
                'nom': 'Test',
                'prenom': 'User',
                'pourcentage': '80'  # Insurance covers 80%, patient pays 20%
            },
            'sections': [{
                'titre': 'Consultation',
                'articles': [{
                    'libelle': 'Examination',
                    'quantite': 2,
                    'montant': 1000  # 2 x 1000 = 2000 total, patient pays 20% = 400
                }]
            }]
        }
        
        with patch('app.InvoicePDF') as mock_pdf_class:
            mock_pdf = MagicMock()
            mock_pdf_class.return_value = mock_pdf
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = 'test.pdf'
                
                response = authenticated_session.post('/generate_invoice/1',
                    data=json.dumps(invoice_data),
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                
                # Verify that the percentage calculation is correct
                # Patient percentage should be 100 - 80 = 20%
                call_args = mock_pdf.add_invoice_sections.call_args[0]
                sections, pourcentage_patient = call_args[0], call_args[1]
                assert pourcentage_patient == 20.0
    
    @patch('app.requests.get')
    def test_invoice_logo_loading(self, mock_requests, authenticated_session):
        """Test that invoice logo loading is handled properly"""
        # Mock successful logo download
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'fake_image_data'
        mock_requests.return_value = mock_response
        
        from app import InvoicePDF
        
        pdf = InvoicePDF()
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = 'logo.png'
            
            # This should not raise an exception
            pdf.header()
        
        # Verify requests were made for logos
        assert mock_requests.call_count >= 1
    
    @patch('app.requests.get')
    def test_invoice_logo_failure_handling(self, mock_requests, authenticated_session):
        """Test that invoice generation handles logo loading failures gracefully"""
        # Mock failed logo download
        mock_requests.side_effect = Exception("Network error")
        
        from app import InvoicePDF
        
        pdf = InvoicePDF()
        
        # This should not raise an exception even if logo loading fails
        try:
            pdf.header()
        except Exception as e:
            pytest.fail(f"Logo loading failure should be handled gracefully, but raised: {e}")
    
    def test_filename_generation(self, authenticated_session):
        """Test that generated PDF filename is correct"""
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
        
        with patch('app.InvoicePDF') as mock_pdf_class:
            mock_pdf = MagicMock()
            mock_pdf_class.return_value = mock_pdf
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = 'test.pdf'
                
                with patch('app.send_file') as mock_send_file:
                    response = authenticated_session.post('/generate_invoice/1',
                        data=json.dumps(invoice_data),
                        content_type='application/json'
                    )
                    
                    # Check that send_file was called with correct filename pattern
                    mock_send_file.assert_called_once()
                    call_kwargs = mock_send_file.call_args[1]
                    filename = call_kwargs['download_name']
                    
                    assert 'facture_Doe_John_' in filename
                    assert filename.endswith('.pdf')
