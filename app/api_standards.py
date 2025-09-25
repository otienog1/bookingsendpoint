"""
API Standards and Response Formatting for the Bookings Application

This module provides standardized response formats and error handling
to ensure consistency across all API endpoints.
"""

from flask import jsonify, request
from functools import wraps
import traceback
from datetime import datetime
from app.schemas import format_validation_errors
from marshmallow import ValidationError


class ApiResponse:
    """Standard API response formatting"""

    @staticmethod
    def success(data=None, message=None, status=200, meta=None):
        """
        Create a standardized success response

        Args:
            data: The response data
            message: Optional success message
            status: HTTP status code (default: 200)
            meta: Optional metadata (pagination, etc.)

        Returns:
            Flask response object
        """
        response_data = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
        }

        if message:
            response_data['message'] = message

        if data is not None:
            response_data['data'] = data

        if meta:
            response_data['meta'] = meta

        return jsonify(response_data), status

    @staticmethod
    def error(message, status=400, error_code=None, details=None):
        """
        Create a standardized error response

        Args:
            message: Error message
            status: HTTP status code
            error_code: Optional error code for client-side handling
            details: Optional additional error details

        Returns:
            Flask response object
        """
        response_data = {
            'success': False,
            'error': message,
            'timestamp': datetime.utcnow().isoformat(),
        }

        if error_code:
            response_data['error_code'] = error_code

        if details:
            response_data['details'] = details

        return jsonify(response_data), status

    @staticmethod
    def validation_error(errors, message="Validation failed"):
        """
        Create a standardized validation error response

        Args:
            errors: Dictionary of field validation errors
            message: Optional custom message

        Returns:
            Flask response object
        """
        return ApiResponse.error(
            message=message,
            status=422,
            error_code='VALIDATION_ERROR',
            details={'validation_errors': errors}
        )

    @staticmethod
    def unauthorized(message="Authentication required"):
        """Create a standardized unauthorized response"""
        return ApiResponse.error(
            message=message,
            status=401,
            error_code='UNAUTHORIZED'
        )

    @staticmethod
    def forbidden(message="Access denied"):
        """Create a standardized forbidden response"""
        return ApiResponse.error(
            message=message,
            status=403,
            error_code='FORBIDDEN'
        )

    @staticmethod
    def not_found(message="Resource not found"):
        """Create a standardized not found response"""
        return ApiResponse.error(
            message=message,
            status=404,
            error_code='NOT_FOUND'
        )

    @staticmethod
    def server_error(message="Internal server error"):
        """Create a standardized server error response"""
        return ApiResponse.error(
            message=message,
            status=500,
            error_code='SERVER_ERROR'
        )

    @staticmethod
    def paginated(data, page, limit, total, message=None):
        """
        Create a paginated response

        Args:
            data: List of items
            page: Current page number
            limit: Items per page
            total: Total number of items
            message: Optional message

        Returns:
            Flask response object
        """
        import math

        total_pages = math.ceil(total / limit) if limit > 0 else 0
        has_next = page < total_pages
        has_prev = page > 1

        meta = {
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev,
                'next_page': page + 1 if has_next else None,
                'prev_page': page - 1 if has_prev else None
            }
        }

        return ApiResponse.success(
            data=data,
            message=message,
            meta=meta
        )


def handle_api_errors(func):
    """
    Decorator to handle common API errors and format responses consistently

    This decorator catches common exceptions and formats them as standardized API responses
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except ValidationError as e:
            return ApiResponse.validation_error(format_validation_errors(e.messages))

        except ValueError as e:
            return ApiResponse.error(str(e), status=400, error_code='BAD_REQUEST')

        except PermissionError as e:
            return ApiResponse.forbidden(str(e))

        except FileNotFoundError as e:
            return ApiResponse.not_found(str(e))

        except Exception as e:
            # Log the full traceback for debugging
            print(f"Unhandled API error in {func.__name__}: {str(e)}")
            print(traceback.format_exc())

            # Return generic error message to client (don't expose internal details)
            return ApiResponse.server_error("An unexpected error occurred. Please try again.")

    return wrapper


def validate_pagination_params():
    """
    Extract and validate pagination parameters from request

    Returns:
        tuple: (page, limit) with defaults applied
    """
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))

        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 20

        return page, limit

    except (ValueError, TypeError):
        return 1, 20


def get_sort_params(allowed_fields):
    """
    Extract and validate sorting parameters from request

    Args:
        allowed_fields: List of fields that can be sorted by

    Returns:
        tuple: (sort_by, sort_order)
    """
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')

    if sort_by not in allowed_fields:
        sort_by = 'created_at'

    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'

    return sort_by, sort_order


def require_json(func):
    """
    Decorator to ensure request contains JSON data

    Returns 400 error if request doesn't contain valid JSON
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return ApiResponse.error(
                "Request must contain JSON data",
                status=400,
                error_code='INVALID_CONTENT_TYPE'
            )

        json_data = request.get_json()
        if json_data is None:
            return ApiResponse.error(
                "Request must contain valid JSON data",
                status=400,
                error_code='INVALID_JSON'
            )

        return func(*args, **kwargs)

    return wrapper


# Standard endpoint patterns for consistency
ENDPOINT_PATTERNS = {
    'auth': {
        'login': '/auth/login',
        'register': '/auth/register',
        'refresh': '/auth/refresh',
        'logout': '/auth/logout',
        'forgot_password': '/auth/forgot-password',
        'reset_password': '/auth/reset-password',
        'verify_email': '/auth/verify-email',
        'profile': '/auth/profile'
    },
    'bookings': {
        'list': '/api/v1/bookings',
        'create': '/api/v1/bookings',
        'get': '/api/v1/bookings/<booking_id>',
        'update': '/api/v1/bookings/<booking_id>',
        'delete': '/api/v1/bookings/<booking_id>',
        'documents': '/api/v1/bookings/<booking_id>/documents',
        'share': '/api/v1/bookings/<booking_id>/share'
    },
    'agents': {
        'list': '/api/v1/agents',
        'create': '/api/v1/agents',
        'get': '/api/v1/agents/<agent_id>',
        'update': '/api/v1/agents/<agent_id>',
        'delete': '/api/v1/agents/<agent_id>'
    },
    'documents': {
        'upload': '/api/v1/documents/upload',
        'download': '/api/v1/documents/<document_id>/download',
        'delete': '/api/v1/documents/<document_id>'
    },
    'dashboard': {
        'stats': '/api/v1/dashboard/stats',
        'revenue': '/api/v1/dashboard/revenue',
        'recent_bookings': '/api/v1/dashboard/recent-bookings',
        'recent_users': '/api/v1/dashboard/recent-users'
    }
}


# HTTP Status Codes Reference
class StatusCodes:
    """HTTP Status codes for consistent usage"""

    # Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204

    # Client Errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429

    # Server Errors
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503


# Error Codes for client-side handling
class ErrorCodes:
    """Standard error codes for client-side error handling"""

    # Authentication & Authorization
    UNAUTHORIZED = 'UNAUTHORIZED'
    FORBIDDEN = 'FORBIDDEN'
    TOKEN_EXPIRED = 'TOKEN_EXPIRED'
    INVALID_CREDENTIALS = 'INVALID_CREDENTIALS'

    # Validation
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    MISSING_REQUIRED_FIELD = 'MISSING_REQUIRED_FIELD'
    INVALID_FORMAT = 'INVALID_FORMAT'

    # Data
    NOT_FOUND = 'NOT_FOUND'
    ALREADY_EXISTS = 'ALREADY_EXISTS'
    CONFLICT = 'CONFLICT'

    # Server
    SERVER_ERROR = 'SERVER_ERROR'
    SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE'

    # Network
    NETWORK_ERROR = 'NETWORK_ERROR'
    TIMEOUT = 'TIMEOUT'