# Blueprint Architecture

## Overview

The itinerary system is split into two separate blueprints for clean separation of concerns:

1. **Itinerary Blueprint** (`/api/itinerary`) - Itinerary management (CRUD + creation)
2. **Scraper Blueprint** (`/api/scraper`) - Raw scraping operations and AI agent features

---

## Blueprint Structure

### 1. Itinerary Blueprint (`itinerarybp.py`)

**Purpose:** Manage itineraries (create, read, update, delete)

**Base Path:** `/api/itinerary`

**Responsibilities:**
- ✅ Create itineraries from Safari Portal URLs
- ✅ List and search itineraries
- ✅ Get single itinerary details
- ✅ Update itinerary data
- ✅ Delete/deactivate itineraries
- ✅ Activate itineraries

**Endpoints:**
```
POST   /api/itinerary/create              - Create new itinerary (scrapes URL)
GET    /api/itinerary/list                - List all itineraries
GET    /api/itinerary/<doc_id>            - Get single itinerary
GET    /api/itinerary/<doc_id>/summary    - Get itinerary summary
GET    /api/itinerary/<doc_id>/daily      - Get daily breakdown
PUT    /api/itinerary/<doc_id>            - Update itinerary
PUT    /api/itinerary/<doc_id>/deactivate - Deactivate itinerary
PUT    /api/itinerary/<doc_id>/activate   - Activate itinerary
DELETE /api/itinerary/<doc_id>            - Delete itinerary
GET    /api/itinerary/search              - Search itineraries
```

---

### 2. Scraper Blueprint (`scraperbp.py`)

**Purpose:** Raw scraping operations and AI-powered analysis

**Base Path:** `/api/scraper`

**Responsibilities:**
- ✅ Low-level scraping operations (if needed independently)
- ✅ AI agent chat
- ✅ AI validation
- ✅ AI improvement suggestions
- ✅ AI summary generation
- ✅ Public itinerary access

**Endpoints:**
```
POST   /api/scraper/scrape                     - Raw scrape (without booking link)
POST   /api/scraper/agent/chat                 - Chat with AI agent
POST   /api/scraper/agent/validate/<doc_id>   - AI validation
POST   /api/scraper/agent/improve/<doc_id>    - AI improvement suggestions
POST   /api/scraper/agent/summary/<doc_id>    - AI summary generation
GET    /api/scraper/public/<doc_id>           - Public itinerary (no auth)
```

---

### 3. Bookings Blueprint (`bookingsbp.py`)

**Related Endpoint:**
```
GET /api/bookings/<booking_id>/itineraries - Get all itineraries for a booking
```

This endpoint lives in the bookings blueprint to keep booking-related operations together.

---

## Design Principles

### Separation of Concerns

**Itinerary Blueprint:**
- User-facing itinerary management
- Enforces booking relationships
- Permission checks
- CRUD operations

**Scraper Blueprint:**
- Technical/infrastructure layer
- AI-powered analysis
- Can work independently of bookings
- Public access features

### Benefits

1. **Clear Responsibility:** Each blueprint has a specific purpose
2. **Maintainability:** Easy to find and update related functionality
3. **Testing:** Can test scraping logic separately from CRUD
4. **Scalability:** Can deploy as microservices if needed
5. **Security:** Different auth requirements per blueprint

---

## Typical Workflow

### Creating an Itinerary

**User Flow:**
1. User creates/selects a booking
2. User pastes Safari Portal URL
3. Frontend calls `POST /api/itinerary/create`
4. Backend:
   - Validates booking exists
   - Checks permissions
   - Scrapes the URL (uses scraper internally)
   - Saves with booking relationship
   - Returns created itinerary

**Code Flow:**
```
itinerarybp.create_itinerary()
  ↓
  Verify booking & permissions
  ↓
  ItineraryScraper.scrape_page()
  ↓
  ItineraryModel.create()
  ↓
  Return saved itinerary
```

### Using AI Features

**User Flow:**
1. User views an itinerary
2. User clicks "Validate" or "Get Suggestions"
3. Frontend calls `POST /api/scraper/agent/validate/<doc_id>`
4. Backend:
   - Loads itinerary
   - Sends to AI agent
   - Returns analysis

**Code Flow:**
```
scraperbp.agent_validate()
  ↓
  ItineraryAgent.validate_itinerary()
  ↓
  Return validation report
```

---

## File Organization

```
backend/app/
├── __init__.py                    # Registers both blueprints
├── itinerarybp.py                 # Itinerary management blueprint
├── bookingsbp.py                  # Includes booking-itinerary endpoint
└── scraper/
    ├── __init__.py
    ├── scraperbp.py               # Scraper & AI blueprint
    ├── itinerary_scraper.py       # Scraping logic
    ├── itinerary_agent.py         # AI agent
    └── itinerary_model.py         # MongoDB model
```

---

## API Usage Examples

### Example 1: Create Itinerary (Typical Use Case)

```bash
POST /api/itinerary/create
{
  "url": "https://safariportal.app/itinerary/123",
  "booking_id": "507f1f77bcf86cd799439011",
  "itinerary_type": "option_1"
}
```

### Example 2: Get All Itineraries for a Booking

```bash
GET /api/bookings/507f1f77bcf86cd799439011/itineraries
```

### Example 3: AI Validation

```bash
POST /api/scraper/agent/validate/507f191e810c19729de860ea
{
  "llm_provider": "gemini"
}
```

### Example 4: Raw Scrape (Advanced)

If you need to scrape without creating a booking relationship:

```bash
POST /api/scraper/scrape
{
  "url": "https://safariportal.app/itinerary/123",
  "headless": true
}
```

---

## Migration from Old Structure

### Old Structure (Single Blueprint)

Previously, everything was in `scraper_bp`:
- `/api/scraper/scrape` - Create itinerary
- `/api/scraper/itineraries` - List itineraries
- `/api/scraper/itineraries/<id>` - CRUD operations
- `/api/scraper/agent/*` - AI features

### New Structure (Two Blueprints)

Now separated into:
- **Itinerary Blueprint:** `/api/itinerary/*` - User-facing CRUD
- **Scraper Blueprint:** `/api/scraper/*` - Technical/AI features

### What Changed

1. ✅ `/api/scraper/scrape` → `/api/itinerary/create` (primary endpoint)
2. ✅ `/api/scraper/itineraries` → `/api/itinerary/list`
3. ✅ `/api/scraper/itineraries/<id>` → `/api/itinerary/<id>`
4. ✅ AI endpoints stay under `/api/scraper/agent/*`
5. ✅ Raw scraping still available at `/api/scraper/scrape` (for advanced use)

---

## When to Use Which Blueprint

### Use Itinerary Blueprint (`/api/itinerary`) when:
- ✅ Creating itineraries for bookings
- ✅ Managing itinerary CRUD operations
- ✅ User-facing features
- ✅ Need booking relationship enforcement

### Use Scraper Blueprint (`/api/scraper`) when:
- ✅ Using AI agent features
- ✅ Need raw scraping without booking
- ✅ Public itinerary sharing
- ✅ Advanced/technical operations

### Use Bookings Blueprint (`/api/bookings`) when:
- ✅ Getting all itineraries for a booking
- ✅ Booking-centric operations

---

## Testing

### Test Itinerary Blueprint

```python
# Test creation with booking
def test_create_itinerary():
    response = client.post('/api/itinerary/create', json={
        'url': 'https://example.com/itinerary/123',
        'booking_id': '507f1f77bcf86cd799439011',
        'itinerary_type': 'option_1'
    })
    assert response.status_code == 200

# Test CRUD operations
def test_list_itineraries():
    response = client.get('/api/itinerary/list')
    assert response.status_code == 200
```

### Test Scraper Blueprint

```python
# Test AI validation
def test_ai_validation():
    response = client.post('/api/scraper/agent/validate/123')
    assert response.status_code == 200

# Test raw scraping
def test_raw_scrape():
    response = client.post('/api/scraper/scrape', json={
        'url': 'https://example.com/itinerary/123'
    })
    assert response.status_code == 200
```

---

## Security Considerations

### Itinerary Blueprint
- ✅ All endpoints require authentication (`@token_required`)
- ✅ Permission checks (user can only create for own bookings)
- ✅ Booking validation before creation

### Scraper Blueprint
- ✅ AI endpoints require authentication
- ✅ Public endpoint (`/public/<id>`) is intentionally unauthenticated
- ✅ Sensitive metadata removed from public access

---

## Future Enhancements

### Potential Features

1. **Batch Operations**
   - `POST /api/itinerary/batch-create` - Create multiple itineraries

2. **Templates**
   - `GET /api/itinerary/templates` - Get itinerary templates

3. **Advanced Scraping**
   - `POST /api/scraper/batch-scrape` - Scrape multiple URLs

4. **AI Features**
   - `POST /api/scraper/agent/compare` - Compare two itineraries
   - `POST /api/scraper/agent/optimize` - Optimize route/schedule

---

## Questions & Support

For questions about:
- **Itinerary CRUD:** Check [itinerarybp.py](app/itinerarybp.py)
- **Scraping Logic:** Check [scraperbp.py](app/scraper/scraperbp.py)
- **API Reference:** See [API_REFERENCE.md](API_REFERENCE.md)
- **Migration:** See [ENDPOINT_CHANGES_SUMMARY.md](ENDPOINT_CHANGES_SUMMARY.md)
