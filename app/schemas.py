"""
Validation schemas using Marshmallow for API request validation
"""

from marshmallow import Schema, fields, validate, validates_schema, ValidationError
from datetime import datetime, date
import re


class EmailField(fields.Email):
    """Custom email field with better error message"""
    default_error_messages = {
        'invalid': 'Please enter a valid email address.'
    }


class PasswordField(fields.String):
    """Custom password field with validation"""
    default_error_messages = {
        'invalid': 'Password must be at least 8 characters long and contain uppercase, lowercase, and numeric characters.'
    }

    def _validate(self, value, attr, data, **kwargs):
        super()._validate(value, attr, data, **kwargs)

        if len(value) < 8:
            raise ValidationError('Password must be at least 8 characters long.')

        if not re.search(r'[A-Z]', value):
            raise ValidationError('Password must contain at least one uppercase letter.')

        if not re.search(r'[a-z]', value):
            raise ValidationError('Password must contain at least one lowercase letter.')

        if not re.search(r'\d', value):
            raise ValidationError('Password must contain at least one number.')


# Authentication Schemas
class LoginSchema(Schema):
    email = EmailField(required=True)
    password = fields.String(required=True, validate=validate.Length(min=1, error='Password is required.'))


class RegisterSchema(Schema):
    first_name = fields.String(required=True, validate=validate.Length(min=2, max=50))
    last_name = fields.String(required=True, validate=validate.Length(min=2, max=50))
    email = EmailField(required=True)
    password = PasswordField(required=True)
    confirm_password = fields.String(required=True)

    @validates_schema
    def validate_passwords_match(self, data, **kwargs):
        if data.get('password') != data.get('confirm_password'):
            raise ValidationError("Passwords don't match.", 'confirm_password')


class ForgotPasswordSchema(Schema):
    email = EmailField(required=True)


class ResetPasswordSchema(Schema):
    token = fields.String(required=True, validate=validate.Length(min=1))
    password = PasswordField(required=True)
    confirm_password = fields.String(required=True)

    @validates_schema
    def validate_passwords_match(self, data, **kwargs):
        if data.get('password') != data.get('confirm_password'):
            raise ValidationError("Passwords don't match.", 'confirm_password')


# Booking Schemas
class BookingCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=2, max=100))
    agent_id = fields.String(required=True, validate=validate.Length(min=1))
    date_from = fields.Date(required=True, format='%Y-%m-%d')
    date_to = fields.Date(required=True, format='%Y-%m-%d')
    pax = fields.Integer(required=True, validate=validate.Range(min=1, max=100))
    rate_basis = fields.String(required=True, validate=validate.OneOf(['Adult', 'Child', 'Family']))
    consultant = fields.String(allow_none=True, validate=validate.Length(max=100))
    notes = fields.String(allow_none=True, validate=validate.Length(max=1000))
    created_by = fields.String(allow_none=True)

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data.get('date_to') and data.get('date_from'):
            if data['date_to'] <= data['date_from']:
                raise ValidationError('End date must be after start date.', 'date_to')

            if data['date_from'] < date.today():
                raise ValidationError('Start date cannot be in the past.', 'date_from')


class BookingUpdateSchema(BookingCreateSchema):
    id = fields.String(required=True, validate=validate.Length(min=1))
    name = fields.String(validate=validate.Length(min=2, max=100))
    agent_id = fields.String(validate=validate.Length(min=1))
    date_from = fields.Date(format='%Y-%m-%d')
    date_to = fields.Date(format='%Y-%m-%d')
    pax = fields.Integer(validate=validate.Range(min=1, max=100))
    rate_basis = fields.String(validate=validate.OneOf(['Adult', 'Child', 'Family']))


# Agent Schemas
class AgentCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=2, max=100))
    email = EmailField(required=True)
    phone = fields.String(required=True, validate=validate.Length(min=10, max=15))
    location = fields.String(required=True, validate=validate.Length(min=2, max=100))
    commission_rate = fields.Float(required=True, validate=validate.Range(min=0, max=100))
    notes = fields.String(allow_none=True, validate=validate.Length(max=500))


class AgentUpdateSchema(AgentCreateSchema):
    id = fields.String(required=True, validate=validate.Length(min=1))
    name = fields.String(validate=validate.Length(min=2, max=100))
    email = EmailField()
    phone = fields.String(validate=validate.Length(min=10, max=15))
    location = fields.String(validate=validate.Length(min=2, max=100))
    commission_rate = fields.Float(validate=validate.Range(min=0, max=100))


# Document Schemas
class DocumentUploadSchema(Schema):
    category = fields.String(required=True, validate=validate.OneOf(['Voucher', 'Air Ticket', 'Invoice', 'Other']))

    # File validation will be handled separately in the route


# Filter Schemas
class BookingFilterSchema(Schema):
    search = fields.String()
    agent_id = fields.String()
    date_from = fields.Date(format='%Y-%m-%d')
    date_to = fields.Date(format='%Y-%m-%d')
    rate_basis = fields.String(validate=validate.OneOf(['Adult', 'Child', 'Family']))
    consultant = fields.String()
    created_by = fields.String()
    page = fields.Integer(validate=validate.Range(min=1))
    limit = fields.Integer(validate=validate.Range(min=1, max=100))
    sort_by = fields.String(validate=validate.OneOf(['name', 'date_from', 'date_to', 'pax', 'created_at']))
    sort_order = fields.String(validate=validate.OneOf(['asc', 'desc']))


class AgentFilterSchema(Schema):
    search = fields.String()
    location = fields.String()
    page = fields.Integer(validate=validate.Range(min=1))
    limit = fields.Integer(validate=validate.Range(min=1, max=100))
    sort_by = fields.String(validate=validate.OneOf(['name', 'email', 'location', 'commission_rate', 'created_at']))
    sort_order = fields.String(validate=validate.OneOf(['asc', 'desc']))


# User Profile Schemas
class ProfileUpdateSchema(Schema):
    first_name = fields.String(required=True, validate=validate.Length(min=2, max=50))
    last_name = fields.String(required=True, validate=validate.Length(min=2, max=50))
    email = EmailField(required=True)


class PasswordChangeSchema(Schema):
    current_password = fields.String(required=True, validate=validate.Length(min=1))
    new_password = PasswordField(required=True)
    confirm_password = fields.String(required=True)

    @validates_schema
    def validate_passwords_match(self, data, **kwargs):
        if data.get('new_password') != data.get('confirm_password'):
            raise ValidationError("New passwords don't match.", 'confirm_password')


# Pagination Schema
class PaginationSchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    limit = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))


# Response Schemas
class SuccessResponseSchema(Schema):
    success = fields.Boolean(load_default=True)
    message = fields.String()
    data = fields.Raw()


class ErrorResponseSchema(Schema):
    success = fields.Boolean(load_default=False)
    error = fields.String()
    details = fields.Dict()


class ValidationErrorResponseSchema(Schema):
    success = fields.Boolean(load_default=False)
    error = fields.String(load_default='Validation failed')
    validation_errors = fields.Dict()


# Helper function to format validation errors
def format_validation_errors(errors):
    """
    Format marshmallow validation errors into a consistent structure
    """
    formatted_errors = {}

    for field, messages in errors.items():
        if isinstance(messages, list):
            formatted_errors[field] = messages[0]  # Take first error message
        else:
            formatted_errors[field] = str(messages)

    return formatted_errors


# Decorator for request validation
def validate_json(schema_class):
    """
    Decorator to validate JSON request data using a Marshmallow schema
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            from flask import request, jsonify

            schema = schema_class()

            try:
                # Get JSON data from request
                json_data = request.get_json()
                if json_data is None:
                    return jsonify({
                        'success': False,
                        'error': 'Request must contain valid JSON data'
                    }), 400

                # Validate and deserialize
                validated_data = schema.load(json_data)

                # Add validated data to request for use in the route
                request.validated_data = validated_data

                return func(*args, **kwargs)

            except ValidationError as err:
                return jsonify({
                    'success': False,
                    'error': 'Validation failed',
                    'validation_errors': format_validation_errors(err.messages)
                }), 422

        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


def validate_query_params(schema_class):
    """
    Decorator to validate query parameters using a Marshmallow schema
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            from flask import request, jsonify

            schema = schema_class()

            try:
                # Get query parameters
                query_params = request.args.to_dict()

                # Convert numeric strings to appropriate types
                for key, value in query_params.items():
                    if key in ['page', 'limit', 'pax', 'commission_rate']:
                        try:
                            if key == 'commission_rate':
                                query_params[key] = float(value)
                            else:
                                query_params[key] = int(value)
                        except (ValueError, TypeError):
                            pass  # Let schema validation handle the error

                # Validate and deserialize
                validated_params = schema.load(query_params)

                # Add validated params to request
                request.validated_params = validated_params

                return func(*args, **kwargs)

            except ValidationError as err:
                return jsonify({
                    'success': False,
                    'error': 'Invalid query parameters',
                    'validation_errors': format_validation_errors(err.messages)
                }), 422

        wrapper.__name__ = func.__name__
        return wrapper
    return decorator