"""
Flask Blueprint for Scraper API

Provides endpoints for scraping Safari Portal pages and AI agent features.
For itinerary management (CRUD), use the itinerary blueprint.
"""

import asyncio
from flask import Blueprint, request

from ..api_standards import ApiResponse
from .itinerary_scraper import ItineraryScraper
from .itinerary_model import ItineraryModel
from .itinerary_agent import ItineraryAgent
from ..authbp import token_required


# Create blueprint for scraping operations
scraperbp = Blueprint('scraper', __name__, url_prefix='/api/scraper')

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


# ============================================================================
# SCRAPING ENDPOINTS
# ============================================================================

@scraperbp.route('/scrape', methods=['POST'])
@token_required
def scrape_itinerary(current_user):
    """
    Scrape an itinerary from a Safari Portal URL and save to database.

    Automatically tries all available LLM models until successful:
    - Google Gemini (free tier)
    - OpenRouter models (Llama 3.1, DeepSeek-R1, Qwen)
    - Hugging Face models
    - Anthropic Claude (as last resort)

    Endpoint: POST /api/scraper/scrape

    Request body:
    {
        "url": "https://example.safariportal.app/itinerary/123",
        "booking_id": "507f1f77bcf86cd799439011",  // Optional - Link itinerary to a booking
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


# ============================================================================
# AI AGENT ENDPOINTS - Assistant for Itinerary Analysis
# ============================================================================

@scraperbp.route('/agent/chat', methods=['POST'])
@token_required
def agent_chat(current_user):
    """
    Chat with the itinerary AI agent.

    Endpoint: POST /api/scraper/agent/chat

    Request body:
    {
        "message": "What activities are planned for day 3?",
        "itinerary_id": "optional_doc_id",
        "conversation_history": [
            {"user": "previous question", "agent": "previous response"}
        ],
        "llm_provider": "gemini"  // optional
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


@scraperbp.route('/agent/validate/<doc_id>', methods=['POST'])
@token_required
def agent_validate(current_user, doc_id):
    """
    Validate an itinerary for completeness and consistency using AI.

    Endpoint: POST /api/scraper/agent/validate/<doc_id>

    Args:
        doc_id: Document ID

    Request body (optional):
    {
        "llm_provider": "gemini"  // optional
    }

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


@scraperbp.route('/agent/improve/<doc_id>', methods=['POST'])
@token_required
def agent_improve(current_user, doc_id):
    """
    Get AI-powered improvement suggestions for an itinerary.

    Endpoint: POST /api/scraper/agent/improve/<doc_id>

    Args:
        doc_id: Document ID

    Request body (optional):
    {
        "llm_provider": "gemini"  // optional
    }

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


@scraperbp.route('/agent/summary/<doc_id>', methods=['POST'])
@token_required
def agent_summary(current_user, doc_id):
    """
    Generate an AI summary of an itinerary.

    Endpoint: POST /api/scraper/agent/summary/<doc_id>

    Request body (optional):
    {
        "summary_type": "overview",  // options: overview, daily, highlights, logistics
        "llm_provider": "gemini"  // optional
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


# ============================================================================
# PUBLIC ENDPOINTS (No Auth Required)
# ============================================================================

@scraperbp.route('/public/<doc_id>', methods=['GET'])
def get_public_itinerary(doc_id):
    """
    Get a public itinerary (for sharing).

    Endpoint: GET /api/scraper/public/<doc_id>

    Args:
        doc_id: Document ID

    Returns:
        Full itinerary document (with sensitive metadata removed)
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
