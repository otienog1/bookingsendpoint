"""
Flask Blueprint for Itinerary Scraper API

Provides endpoints for scraping Safari Portal pages,
viewing scraped itineraries, and managing the data.
"""

import asyncio
from flask import Blueprint, request, jsonify, g

from ..api_standards import ApiResponse
from .itinerary_scraper import ItineraryScraper
from .itinerary_model import ItineraryModel
from .itinerary_agent import ItineraryAgent
from ..authbp import token_required


# Create blueprint for itinerary endpoints
scraper_bp = Blueprint('scraper', __name__, url_prefix='/api/itinerary')

# Store model and agent instances (initialized in init)
_model = None
_agent = None


def get_model():
    """Get or create the itinerary model."""
    global _model
    if _model is None:
        from .. import mongo
        _model = ItineraryModel(mongo)
        _model.ensure_indexes()
    return _model


def get_agent(llm_provider='gemini'):
    """Get or create the itinerary agent."""
    global _agent
    if _agent is None:
        from .. import mongo
        _agent = ItineraryAgent(mongo, llm_provider=llm_provider)
    return _agent


@scraper_bp.route('/create', methods=['POST'])
@token_required
def create_itinerary(current_user):
    """
    Create a new itinerary by scraping a Safari Portal URL.

    Automatically tries all available LLM models until successful:
    - Google Gemini (free tier)
    - OpenRouter models (Llama 3.1, DeepSeek-R1, Qwen)
    - Hugging Face models
    - Anthropic Claude (as last resort)

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

    url = data['url']
    headless = data.get('headless', True)
    booking_id = data.get('booking_id', None)
    itinerary_type = data.get('itinerary_type', 'option_1')
    version = data.get('version', 1)

    try:
        # Get MongoDB connection
        from .. import mongo

        # Create scraper with MongoDB client (will auto-detect available API keys)
        scraper = ItineraryScraper(mongo)

        # Run the async scraping
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Scrape the page
            raw_data = loop.run_until_complete(
                scraper.scrape_page(url, headless)
            )

            # Transform with Claude
            structured_data = scraper.transform_with_claude(raw_data)

            # Check for transformation errors
            if 'error' in structured_data:
                error_msg = f"Transformation failed: {structured_data.get('error')}"
                raw_response = structured_data.get('raw_response', '')
                if raw_response:
                    error_msg += f"\n\nRaw response preview: {raw_response[:500]}"
                return ApiResponse.error(error_msg, status=500)

            # Save to MongoDB using model
            model = get_model()
            user_id = str(current_user.get('_id')) if current_user else None
            doc_id = model.create(structured_data, user_id, url, booking_id, itinerary_type, version)

            # Retrieve the saved document with proper serialization
            saved_doc = model.find_by_id(doc_id)

            # Convert datetime objects to ISO strings for JSON serialization
            if saved_doc and '_metadata' in saved_doc:
                for key, value in saved_doc['_metadata'].items():
                    if hasattr(value, 'isoformat'):
                        saved_doc['_metadata'][key] = value.isoformat()

            # Return full structured data along with document ID
            response_data = {
                'document_id': doc_id,
                'message': 'Itinerary scraped and saved successfully',
                'itinerary': saved_doc
            }
            return ApiResponse.success(response_data)

        finally:
            loop.close()

    except Exception as e:
        return ApiResponse.error(f'Scraping failed: {str(e)}', status=500)


@scraper_bp.route('/list', methods=['GET'])
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
            'scraped_at': item.get('_metadata', {}).get('scraped_at')
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


@scraper_bp.route('/<doc_id>', methods=['GET'])
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


@scraper_bp.route('/<doc_id>/summary', methods=['GET'])
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


@scraper_bp.route('/<doc_id>/daily', methods=['GET'])
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


@scraper_bp.route('/<doc_id>', methods=['DELETE'])
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


@scraper_bp.route('/<doc_id>/deactivate', methods=['PUT'])
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


# Note: The endpoint GET /api/bookings/<booking_id>/itineraries
# has been moved to bookingsbp.py to keep booking-related endpoints together


@scraper_bp.route('/search', methods=['GET'])
@token_required
def search_itineraries(current_user):
    """
    Search itineraries by tour name or client.

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
            'countries': overview.get('countries_visited', [])
        })

    return ApiResponse.success({
        'items': summaries,
        'total': len(summaries)
    })


# Public endpoint for shared itineraries (no auth required)
@scraper_bp.route('/public/<doc_id>', methods=['GET'])
def get_public_itinerary(doc_id):
    """
    Get a public itinerary (for sharing).

    Args:
        doc_id: Document ID

    Returns:
        Full itinerary document
    """
    model = get_model()
    doc = model.find_by_id(doc_id)

    if not doc:
        return ApiResponse.error('Itinerary not found', status=404)

    # Remove sensitive metadata
    if '_metadata' in doc:
        doc['_metadata'] = {
            'scraped_at': doc['_metadata'].get('scraped_at')
        }

    return ApiResponse.success(doc)


# ============================================================================
# AGENT ENDPOINTS - AI Assistant for Itinerary Management
# ============================================================================

@scraper_bp.route('/agent/chat', methods=['POST'])
@token_required
def agent_chat(current_user):
    """
    Chat with the itinerary agent.

    Request body:
    {
        "message": "What activities are planned for day 3?",
        "itinerary_id": "optional_doc_id",
        "conversation_history": [
            {"user": "previous question", "agent": "previous response"}
        ]
    }

    Returns:
        Agent response with timestamp
    """
    data = request.get_json()

    if not data or 'message' not in data:
        return ApiResponse.error('Message is required', status=400)

    message = data['message']
    itinerary_id = data.get('itinerary_id')
    conversation_history = data.get('conversation_history', [])
    llm_provider = data.get('llm_provider', 'gemini')

    try:
        agent = get_agent(llm_provider)
        response = agent.chat(
            message=message,
            itinerary_id=itinerary_id,
            conversation_history=conversation_history
        )
        return ApiResponse.success(response)
    except Exception as e:
        return ApiResponse.error(f'Chat failed: {str(e)}', status=500)


@scraper_bp.route('/agent/validate/<doc_id>', methods=['POST'])
@token_required
def agent_validate(current_user, doc_id):
    """
    Validate an itinerary for completeness and consistency.

    Args:
        doc_id: Document ID

    Returns:
        Validation report with issues and suggestions
    """
    llm_provider = request.get_json().get('llm_provider', 'gemini') if request.get_json() else 'gemini'

    try:
        agent = get_agent(llm_provider)
        report = agent.validate_itinerary(doc_id)

        if 'error' in report:
            return ApiResponse.error(report['error'], status=404)

        return ApiResponse.success(report)
    except Exception as e:
        return ApiResponse.error(f'Validation failed: {str(e)}', status=500)


@scraper_bp.route('/agent/improve/<doc_id>', methods=['POST'])
@token_required
def agent_improve(current_user, doc_id):
    """
    Get improvement suggestions for an itinerary.

    Args:
        doc_id: Document ID

    Returns:
        Improvement suggestions
    """
    llm_provider = request.get_json().get('llm_provider', 'gemini') if request.get_json() else 'gemini'

    try:
        agent = get_agent(llm_provider)
        suggestions = agent.suggest_improvements(doc_id)

        if 'error' in suggestions:
            return ApiResponse.error(suggestions['error'], status=404)

        return ApiResponse.success(suggestions)
    except Exception as e:
        return ApiResponse.error(f'Improvement suggestions failed: {str(e)}', status=500)


@scraper_bp.route('/agent/summary/<doc_id>', methods=['POST'])
@token_required
def agent_summary(current_user, doc_id):
    """
    Generate a summary of an itinerary.

    Request body (optional):
    {
        "summary_type": "overview|daily|highlights|logistics",
        "llm_provider": "gemini|anthropic"
    }

    Args:
        doc_id: Document ID

    Returns:
        Generated summary
    """
    data = request.get_json() or {}
    summary_type = data.get('summary_type', 'overview')
    llm_provider = data.get('llm_provider', 'gemini')

    if summary_type not in ['overview', 'daily', 'highlights', 'logistics']:
        return ApiResponse.error(
            'Invalid summary_type. Must be: overview, daily, highlights, or logistics',
            status=400
        )

    try:
        agent = get_agent(llm_provider)
        summary = agent.generate_summary(doc_id, summary_type)

        if 'error' in summary:
            return ApiResponse.error(summary['error'], status=404)

        return ApiResponse.success(summary)
    except Exception as e:
        return ApiResponse.error(f'Summary generation failed: {str(e)}', status=500)
