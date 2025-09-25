"""
Pytest configuration and fixtures for the Flask application tests.
"""
import pytest
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    return app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test runner for the Flask application."""
    return app.test_cli_runner()


@pytest.fixture
def sample_booking_data():
    """Sample booking data for tests."""
    return {
        'name': 'Test Booking',
        'agent_id': '507f1f77bcf86cd799439011',
        'date_from': '2025-01-01',
        'date_to': '2025-01-07',
        'pax': 2,
        'rate_basis': 'Adult',
        'consultant': 'Test Consultant',
        'notes': 'Test notes'
    }


@pytest.fixture
def sample_agent_data():
    """Sample agent data for tests."""
    return {
        'name': 'Test Agent',
        'email': 'test@example.com',
        'phone': '1234567890',
        'location': 'Test Location',
        'commission_rate': 10.5,
        'notes': 'Test agent notes'
    }