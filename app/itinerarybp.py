"""
Flask Blueprint for Itinerary Management API

Provides endpoints for managing itineraries (CRUD operations and creation via scraping).
"""

import asyncio
from flask import Blueprint, request, current_app
from bson import ObjectId
import traceback

from .api_standards import ApiResponse
from .scraper.itinerary_model import ItineraryModel
from .scraper.itinerary_scraper import ItineraryScraper
from .authbp import token_required
from .mongodb_models import Booking
from . import mongo


# Create blueprint for itinerary management
itinerarybp = Blueprint('itinerary', __name__, url_prefix='/api/itinerary')


def get_model():
    """Get or create the itinerary model."""
    return ItineraryModel(mongo)


# ============================================================================
# CREATE ITINERARY (via Scraping)
# ============================================================================

@itinerarybp.route('/create', methods=['POST'])
@token_required
def create_itinerary(current_user):
    """
    Create a new itinerary by scraping a Safari Portal URL.

    Endpoint: POST /api/itinerary/create

    Request body:
    {
        "url": "https://example.safariportal.app/itinerary/123",
        "booking_id": "507f1f77bcf86cd799439011",  // Required - Link itinerary to a booking
        "itinerary_type": "option_1",  // Type: 'option_1', 'option_2', 'extension', 'final' (default: 'option_1')
        "version": 1,  // Version number (default: 1)
        "headless": true  // optional, default true
    }

    Returns:
        Scraped and transformed itinerary data
    """
    data = request.get_json()

    if not data or 'url' not in data:
        return ApiResponse.error('URL is required', status=400)

    if not data.get('booking_id'):
        return ApiResponse.error('booking_id is required', status=400)

    url = data['url']
    booking_id = data['booking_id']
    headless = data.get('headless', True)
    itinerary_type = data.get('itinerary_type', 'option_1')
    version = data.get('version', 1)

    try:
        # Verify booking exists
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return ApiResponse.error('Booking not found', status=404)

        # Check permissions (booking owner or admin)
        if str(booking['user_id']) != str(current_user['_id']) and current_user['role'] != 'admin':
            return ApiResponse.error('Unauthorized: You can only create itineraries for your own bookings', status=403)

        # Create scraper
        scraper = ItineraryScraper(mongo)

        # Run the async scraping
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Scrape the page
            raw_data = loop.run_until_complete(
                scraper.scrape_page(url, headless)
            )

            # Transform with AI
            structured_data = scraper.transform_with_claude(raw_data)

            # Check for transformation errors
            if 'error' in structured_data:
                error_msg = f"Transformation failed: {structured_data.get('error')}"
                raw_response = structured_data.get('raw_response', '')
                if raw_response:
                    error_msg += f"\n\nRaw response preview: {raw_response[:500]}"
                return ApiResponse.error(error_msg, status=500)

            # Save to MongoDB
            model = get_model()
            user_id = str(current_user.get('_id')) if current_user else None
            doc_id = model.create(structured_data, user_id, url, booking_id, itinerary_type, version)

            # Retrieve the saved document
            saved_doc = model.find_by_id(doc_id)

            # Convert datetime objects to ISO strings for JSON serialization
            if saved_doc and '_metadata' in saved_doc:
                for key, value in saved_doc['_metadata'].items():
                    if hasattr(value, 'isoformat'):
                        saved_doc['_metadata'][key] = value.isoformat()

            # Return full structured data along with document ID
            response_data = {
                'document_id': doc_id,
                'message': 'Itinerary created and saved successfully',
                'itinerary': saved_doc
            }
            return ApiResponse.success(response_data)

        finally:
            loop.close()

    except Exception as e:
        current_app.logger.error(f"Error creating itinerary: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return ApiResponse.error(f'Creation failed: {str(e)}', status=500)


# ============================================================================
# ITINERARY CRUD OPERATIONS
# ============================================================================

@itinerarybp.route('/list', methods=['GET'])
@token_required
def list_itineraries(current_user):
    """
    List all scraped itineraries with pagination.

    Endpoint: GET /api/itinerary/list

    Query params:
        page: Page number (default 1)
        per_page: Items per page (default 20)
        search: Text search query
        sort_by: Field to sort by
        sort_order: asc or desc
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', None)
    sort_by = request.args.get('sort_by', '_metadata.scraped_at')
    sort_order = -1 if request.args.get('sort_order', 'desc') == 'desc' else 1

    model = get_model()
    result = model.find_all(
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search
    )

    # Convert to summaries for list view
    summaries = []
    for item in result['items']:
        overview = item.get('trip_overview', {})
        daily = item.get('daily_itinerary', [])
        summaries.append({
            '_id': item['_id'],
            'tour_name': overview.get('tour_name', 'Unknown'),
            'client_group': overview.get('client_group', ''),
            'dates': overview.get('dates', ''),
            'duration': overview.get('duration', ''),
            'days': len(daily),
            'countries': overview.get('countries_visited', []),
            'scraped_at': item.get('_metadata', {}).get('scraped_at'),
            'booking_id': item.get('booking_id'),
            'itinerary_type': item.get('itinerary_type', 'option_1'),
            'is_active': item.get('is_active', True)
        })

    return ApiResponse.success({
        'items': summaries,
        'pagination': {
            'total': result['total'],
            'page': result['page'],
            'per_page': result['per_page'],
            'pages': result['pages']
        }
    })


@itinerarybp.route('/<doc_id>', methods=['GET'])
@token_required
def get_itinerary(current_user, doc_id):
    """
    Get a single itinerary by ID.

    Endpoint: GET /api/itinerary/<doc_id>

    Args:
        doc_id: Document ID

    Returns:
        Full itinerary document
    """
    model = get_model()
    doc = model.find_by_id(doc_id)

    if not doc:
        return ApiResponse.error('Itinerary not found', status=404)

    return ApiResponse.success(doc)


@itinerarybp.route('/<doc_id>/summary', methods=['GET'])
@token_required
def get_itinerary_summary(current_user, doc_id):
    """
    Get a summary of an itinerary.

    Endpoint: GET /api/itinerary/<doc_id>/summary

    Args:
        doc_id: Document ID

    Returns:
        Itinerary summary
    """
    model = get_model()
    summary = model.get_summary(doc_id)

    if not summary:
        return ApiResponse.error('Itinerary not found', status=404)

    return ApiResponse.success(summary)


@itinerarybp.route('/<doc_id>/daily', methods=['GET'])
@token_required
def get_itinerary_daily(current_user, doc_id):
    """
    Get daily summaries of an itinerary.

    Endpoint: GET /api/itinerary/<doc_id>/daily

    Args:
        doc_id: Document ID

    Returns:
        List of daily summaries
    """
    model = get_model()
    daily = model.get_daily_summary(doc_id)

    if not daily:
        return ApiResponse.error('Itinerary not found', status=404)

    return ApiResponse.success(daily)


@itinerarybp.route('/<doc_id>', methods=['PUT'])
@token_required
def update_itinerary(current_user, doc_id):
    """
    Update an itinerary.

    Endpoint: PUT /api/itinerary/<doc_id>

    Args:
        doc_id: Document ID

    Request body:
        Partial or full itinerary data to update

    Returns:
        Success message
    """
    data = request.get_json()

    if not data:
        return ApiResponse.error('No data provided', status=400)

    model = get_model()

    # Check if itinerary exists
    existing = model.find_by_id(doc_id)
    if not existing:
        return ApiResponse.error('Itinerary not found', status=404)

    # Perform update
    if model.update(doc_id, data):
        return ApiResponse.success({'message': 'Itinerary updated successfully'})
    else:
        return ApiResponse.error('Update failed', status=500)


@itinerarybp.route('/<doc_id>', methods=['DELETE'])
@token_required
def delete_itinerary(current_user, doc_id):
    """
    Delete an itinerary (permanent).

    Endpoint: DELETE /api/itinerary/<doc_id>

    Args:
        doc_id: Document ID

    Returns:
        Success message
    """
    model = get_model()

    if model.delete(doc_id):
        return ApiResponse.success({'message': 'Itinerary deleted successfully'})
    else:
        return ApiResponse.error('Itinerary not found', status=404)


@itinerarybp.route('/<doc_id>/deactivate', methods=['PUT'])
@token_required
def deactivate_itinerary(current_user, doc_id):
    """
    Deactivate an itinerary (soft delete).

    Endpoint: PUT /api/itinerary/<doc_id>/deactivate

    Args:
        doc_id: Document ID

    Returns:
        Success message
    """
    model = get_model()

    if model.deactivate_itinerary(doc_id):
        return ApiResponse.success({'message': 'Itinerary deactivated successfully'})
    else:
        return ApiResponse.error('Itinerary not found', status=404)


@itinerarybp.route('/<doc_id>/activate', methods=['PUT'])
@token_required
def activate_itinerary(current_user, doc_id):
    """
    Activate an itinerary (undo soft delete).

    Endpoint: PUT /api/itinerary/<doc_id>/activate

    Args:
        doc_id: Document ID

    Returns:
        Success message
    """
    model = get_model()

    # Update to set is_active to True
    result = model.get_collection().update_one(
        {'_id': ObjectId(doc_id)},
        {'$set': {'is_active': True}}
    )

    if result.modified_count > 0:
        return ApiResponse.success({'message': 'Itinerary activated successfully'})
    else:
        return ApiResponse.error('Itinerary not found or already active', status=404)


@itinerarybp.route('/search', methods=['GET'])
@token_required
def search_itineraries(current_user):
    """
    Search itineraries by tour name or client.

    Endpoint: GET /api/itinerary/search

    Query params:
        q: Search query
        type: 'tour' or 'client' (default: both)
    """
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'all')

    if not query:
        return ApiResponse.error('Search query is required', status=400)

    model = get_model()
    results = []

    if search_type in ['tour', 'all']:
        tours = model.find_by_tour_name(query)
        results.extend(tours)

    if search_type in ['client', 'all']:
        clients = model.find_by_client(query)
        # Avoid duplicates
        existing_ids = {r['_id'] for r in results}
        for client in clients:
            if client['_id'] not in existing_ids:
                results.append(client)

    # Convert to summaries
    summaries = []
    for item in results:
        overview = item.get('trip_overview', {})
        daily = item.get('daily_itinerary', [])
        summaries.append({
            '_id': item['_id'],
            'tour_name': overview.get('tour_name', 'Unknown'),
            'client_group': overview.get('client_group', ''),
            'dates': overview.get('dates', ''),
            'days': len(daily),
            'countries': overview.get('countries_visited', []),
            'booking_id': item.get('booking_id'),
            'itinerary_type': item.get('itinerary_type', 'option_1'),
            'is_active': item.get('is_active', True)
        })

    return ApiResponse.success({
        'items': summaries,
        'total': len(summaries)
    })


# Note: The endpoint GET /api/bookings/<booking_id>/itineraries
# is located in bookingsbp.py to keep booking-related endpoints together
