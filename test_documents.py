import unittest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from app import create_app
from app.documentsbp import generate_share_token, verify_share_token
import time

class DocumentAPITestCase(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['MONGO_URI'] = 'mongodb://localhost:27017/bookings_test_db'
        self.app.config['SHARE_TOKEN_SECRET'] = 'test-secret'
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Mock user and booking data
        self.test_user_id = "507f1f77bcf86cd799439011"
        self.test_booking_id = "507f1f77bcf86cd799439012"
        self.test_token = "test-jwt-token"

    def tearDown(self):
        """Clean up after tests."""
        self.ctx.pop()

    def test_generate_share_token(self):
        """Test share token generation."""
        booking_id = self.test_booking_id
        categories = ['Voucher', 'Air Ticket']
        expires_in = 3600  # 1 hour

        token, expires_at = generate_share_token(booking_id, categories, expires_in)

        # Verify token format
        self.assertIsInstance(token, str)
        self.assertIn('.', token)  # Should have signature separator

        # Verify expiration time
        expected_expires = int(time.time()) + expires_in
        self.assertAlmostEqual(expires_at, expected_expires, delta=5)

    def test_verify_share_token(self):
        """Test share token verification."""
        booking_id = self.test_booking_id
        categories = ['Voucher', 'Air Ticket']
        expires_in = 3600

        # Generate token
        token, _ = generate_share_token(booking_id, categories, expires_in)

        # Verify token
        payload = verify_share_token(token)

        self.assertIsNotNone(payload)
        self.assertEqual(payload['booking_id'], booking_id)
        self.assertEqual(payload['categories'], categories)
        self.assertEqual(payload['type'], 'share')

    def test_verify_expired_token(self):
        """Test verification of expired token."""
        booking_id = self.test_booking_id
        categories = ['Voucher']
        expires_in = -3600  # Expired 1 hour ago

        token, _ = generate_share_token(booking_id, categories, expires_in)
        payload = verify_share_token(token)

        self.assertIsNone(payload)

    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.format"
        payload = verify_share_token(invalid_token)
        self.assertIsNone(payload)

    @patch('app.documentsbp.mongo')
    @patch('app.documentsbp.token_required')
    def test_get_documents_unauthorized(self, mock_token_required, mock_mongo):
        """Test getting documents without proper authorization."""
        # Mock user without access to booking
        mock_user = {
            '_id': "different_user_id",
            'username': 'testuser',
            'role': 'user'
        }

        # Mock booking owned by different user
        mock_booking = {
            '_id': self.test_booking_id,
            'user_id': self.test_user_id,
            'name': 'Test Booking'
        }

        mock_token_required.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_mongo.db.bookings.find_one.return_value = mock_booking

        response = self.client.get(f'/api/bookings/{self.test_booking_id}/documents')

        # Should return 403 for unauthorized access
        self.assertEqual(response.status_code, 403)

    @patch('app.documentsbp.mongo')
    @patch('app.documentsbp.token_required')
    def test_get_documents_success(self, mock_token_required, mock_mongo):
        """Test successfully getting documents."""
        # Mock authorized user (booking owner)
        mock_user = {
            '_id': self.test_user_id,
            'username': 'testuser',
            'role': 'user'
        }

        mock_booking = {
            '_id': self.test_booking_id,
            'user_id': self.test_user_id,
            'name': 'Test Booking',
            'itinerary_url': 'https://example.com/itinerary'
        }

        mock_documents = [
            {
                '_id': 'doc1',
                'filename': 'voucher.pdf',
                'category': 'Voucher',
                'size': 1024,
                'uploaded_at': '2023-01-01T00:00:00',
                'url': 'http://copyparty.com/file1',
                'mime_type': 'application/pdf',
                'booking_id': self.test_booking_id
            }
        ]

        mock_token_required.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)

        # Mock database calls
        from app.mongodb_models import Booking
        with patch.object(Booking, 'find_by_id', return_value=mock_booking):
            mock_mongo.db.booking_documents.find.return_value = mock_documents

            response = self.client.get(f'/api/bookings/{self.test_booking_id}/documents')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('documents', data)
            self.assertIn('itineraryUrl', data)
            self.assertEqual(len(data['documents']), 1)

    @patch('app.documentsbp.upload_to_copyparty')
    @patch('app.documentsbp.mongo')
    @patch('app.documentsbp.token_required')
    def test_upload_document_success(self, mock_token_required, mock_mongo, mock_upload):
        """Test successful document upload."""
        # Mock authorized user
        mock_user = {
            '_id': self.test_user_id,
            'username': 'testuser',
            'role': 'user'
        }

        mock_booking = {
            '_id': self.test_booking_id,
            'user_id': self.test_user_id,
            'name': 'Test Booking'
        }

        # Mock successful upload to Copyparty
        mock_upload.return_value = {
            'url': 'http://copyparty.com/uploaded_file.pdf',
            'filename': 'uploaded_file.pdf',
            'original_filename': 'test_file.pdf',
            'path': 'bookings/123/Voucher/uploaded_file.pdf',
            'size': 1024
        }

        mock_token_required.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)

        # Mock database operations
        from app.mongodb_models import Booking
        with patch.object(Booking, 'find_by_id', return_value=mock_booking):
            mock_mongo.db.booking_documents.count_documents.return_value = 0
            mock_mongo.db.booking_documents.insert_one.return_value = MagicMock(inserted_id='new_doc_id')

            # Create test file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(b'test content')
                tmp_file_path = tmp_file.name

            try:
                with open(tmp_file_path, 'rb') as test_file:
                    response = self.client.post(
                        f'/api/bookings/{self.test_booking_id}/documents',
                        data={
                            'file': (test_file, 'test_file.pdf'),
                            'category': 'Voucher'
                        },
                        content_type='multipart/form-data'
                    )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertIn('document', data)
                self.assertEqual(data['document']['filename'], 'test_file.pdf')
                self.assertEqual(data['document']['category'], 'Voucher')
            finally:
                os.unlink(tmp_file_path)

    def test_upload_document_invalid_file_type(self):
        """Test upload with invalid file type."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(b'test content')
            tmp_file_path = tmp_file.name

        try:
            with open(tmp_file_path, 'rb') as test_file:
                response = self.client.post(
                    f'/api/bookings/{self.test_booking_id}/documents',
                    data={
                        'file': (test_file, 'test_file.txt'),
                        'category': 'Voucher'
                    },
                    content_type='multipart/form-data',
                    headers={'Authorization': f'Bearer {self.test_token}'}
                )

            # Should fail due to invalid file type
            self.assertNotEqual(response.status_code, 200)
        finally:
            os.unlink(tmp_file_path)

class CopypartyIntegrationTestCase(unittest.TestCase):
    """Test Copyparty integration functions."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    @patch('app.documentsbp.requests')
    def test_upload_to_copyparty_success(self, mock_requests):
        """Test successful upload to Copyparty."""
        from app.documentsbp import upload_to_copyparty

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response

        # Create mock file
        mock_file = MagicMock()
        mock_file.content_type = 'application/pdf'
        mock_file.read.return_value = b'test content'

        result = upload_to_copyparty(mock_file, 'booking123', 'Voucher', 'test.pdf')

        self.assertIsNotNone(result)
        self.assertIn('url', result)
        self.assertIn('filename', result)
        self.assertEqual(result['original_filename'], 'test.pdf')

    @patch('app.documentsbp.requests')
    def test_upload_to_copyparty_failure(self, mock_requests):
        """Test failed upload to Copyparty."""
        from app.documentsbp import upload_to_copyparty

        # Mock failed response
        mock_requests.post.side_effect = Exception("Connection failed")

        mock_file = MagicMock()
        mock_file.content_type = 'application/pdf'
        mock_file.read.return_value = b'test content'

        with self.assertRaises(Exception):
            upload_to_copyparty(mock_file, 'booking123', 'Voucher', 'test.pdf')

if __name__ == '__main__':
    unittest.main()