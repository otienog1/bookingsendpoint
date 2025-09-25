"""
Unit tests for API standards and response formatting.
"""
import pytest
from app.api_standards import ApiResponse


class TestApiResponse:
    """Test the ApiResponse class methods."""

    def test_success_response_basic(self, app):
        """Test basic success response format."""
        with app.app_context():
            response, status = ApiResponse.success()

        assert status == 200
        response_data = response.get_json()
        assert response_data['success'] is True
        assert 'timestamp' in response_data
        assert response_data.get('data') is None
        assert response_data.get('message') is None

    def test_success_response_with_data(self):
        """Test success response with data."""
        test_data = {'test': 'value'}
        response, status = ApiResponse.success(data=test_data, message='Success!')

        assert status == 200
        response_data = response.get_json()
        assert response_data['success'] is True
        assert response_data['data'] == test_data
        assert response_data['message'] == 'Success!'

    def test_error_response_basic(self):
        """Test basic error response format."""
        response, status = ApiResponse.error('Test error')

        assert status == 400
        response_data = response.get_json()
        assert response_data['success'] is False
        assert response_data['error'] == 'Test error'
        assert 'timestamp' in response_data

    def test_error_response_with_details(self):
        """Test error response with additional details."""
        error_details = {'field': 'validation failed'}
        response, status = ApiResponse.error(
            'Validation error',
            status=422,
            error_code='VALIDATION_ERROR',
            details=error_details
        )

        assert status == 422
        response_data = response.get_json()
        assert response_data['success'] is False
        assert response_data['error'] == 'Validation error'
        assert response_data['error_code'] == 'VALIDATION_ERROR'
        assert response_data['details'] == error_details

    def test_validation_error_response(self):
        """Test validation error response format."""
        errors = {'name': 'This field is required'}
        response, status = ApiResponse.validation_error(errors)

        assert status == 422
        response_data = response.get_json()
        assert response_data['success'] is False
        assert response_data['error'] == 'Validation failed'
        assert response_data['error_code'] == 'VALIDATION_ERROR'
        assert response_data['details']['validation_errors'] == errors

    def test_unauthorized_response(self):
        """Test unauthorized response format."""
        response, status = ApiResponse.unauthorized()

        assert status == 401
        response_data = response.get_json()
        assert response_data['success'] is False
        assert response_data['error'] == 'Authentication required'
        assert response_data['error_code'] == 'UNAUTHORIZED'

    def test_not_found_response(self):
        """Test not found response format."""
        response, status = ApiResponse.not_found('Resource not found')

        assert status == 404
        response_data = response.get_json()
        assert response_data['success'] is False
        assert response_data['error'] == 'Resource not found'
        assert response_data['error_code'] == 'NOT_FOUND'

    def test_paginated_response(self):
        """Test paginated response format."""
        test_data = [{'id': 1}, {'id': 2}]
        response, status = ApiResponse.paginated(test_data, page=1, limit=10, total=25)

        assert status == 200
        response_data = response.get_json()
        assert response_data['success'] is True
        assert response_data['data'] == test_data
        assert 'meta' in response_data

        pagination = response_data['meta']['pagination']
        assert pagination['page'] == 1
        assert pagination['limit'] == 10
        assert pagination['total'] == 25
        assert pagination['total_pages'] == 3
        assert pagination['has_next'] is True
        assert pagination['has_prev'] is False