# Itinerary API Reference

## Quick Reference

### Itinerary Endpoints

Base path: `/api/itinerary`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/create` | Create new itinerary from URL |
| GET | `/list` | List all itineraries (paginated) |
| GET | `/<doc_id>` | Get single itinerary |
| GET | `/<doc_id>/summary` | Get itinerary summary |
| GET | `/<doc_id>/daily` | Get daily breakdown |
| PUT | `/<doc_id>/deactivate` | Deactivate itinerary (soft delete) |
| DELETE | `/<doc_id>` | Delete itinerary (permanent) |
| GET | `/search` | Search itineraries by tour/client |

### Booking-Itinerary Endpoints

Base path: `/api/bookings`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/<booking_id>/itineraries` | Get all itineraries for a booking |

---

## Detailed Endpoints

### POST /api/itinerary/create

Create a new itinerary by scraping a Safari Portal URL and linking it to a booking.

**Request Body:**
```json
{
  "url": "https://example.safariportal.app/itinerary/123",
  "booking_id": "507f1f77bcf86cd799439011",
  "itinerary_type": "option_1",
  "version": 1,
  "headless": true
}
```

**Parameters:**
- `url` (string, required) - Safari Portal itinerary URL
- `booking_id` (string, required) - MongoDB ObjectId of the booking
- `itinerary_type` (string, optional) - Type of itinerary (default: `option_1`)
  - Options: `option_1`, `option_2`, `extension`, `final`, `revised`, etc.
- `version` (number, optional) - Version number (default: `1`)
- `headless` (boolean, optional) - Run browser in headless mode (default: `true`)

**Response:**
```json
{
  "success": true,
  "data": {
    "document_id": "507f191e810c19729de860ea",
    "message": "Itinerary scraped and saved successfully",
    "itinerary": { /* full itinerary object */ }
  }
}
```

---

### GET /api/bookings/:booking_id/itineraries

Get all itineraries associated with a specific booking.

**URL Parameters:**
- `booking_id` (string, required) - MongoDB ObjectId of the booking

**Query Parameters:**
- `active_only` (boolean, optional) - Only return active itineraries (default: `true`)
- `type` (string, optional) - Filter by itinerary type

**Examples:**

Get all active itineraries:
```bash
GET /api/bookings/507f1f77bcf86cd799439011/itineraries
```

Get only "option_1" type:
```bash
GET /api/bookings/507f1f77bcf86cd799439011/itineraries?type=option_1
```

Get all itineraries (including inactive):
```bash
GET /api/bookings/507f1f77bcf86cd799439011/itineraries?active_only=false
```

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "_id": "507f191e810c19729de860ea",
        "booking_id": "507f1f77bcf86cd799439011",
        "itinerary_type": "option_1",
        "version": 1,
        "is_active": true,
        "trip_overview": { /* ... */ },
        /* ... other itinerary fields ... */
      }
    ],
    "total": 1
  }
}
```

---

### GET /api/itinerary/:doc_id

Get a single itinerary by its ID.

**URL Parameters:**
- `doc_id` (string, required) - MongoDB ObjectId of the itinerary

**Response:**
```json
{
  "success": true,
  "data": {
    "_id": "507f191e810c19729de860ea",
    "booking_id": "507f1f77bcf86cd799439011",
    "itinerary_type": "option_1",
    "version": 1,
    "is_active": true,
    "trip_overview": {
      "tour_name": "10-Day Kenya Safari",
      "dates": "Jan 15-25, 2025",
      "duration": "10 days / 9 nights",
      /* ... */
    },
    "daily_itinerary": [ /* ... */ ],
    /* ... other fields ... */
  }
}
```

---

### GET /api/itinerary/:doc_id/summary

Get a lightweight summary of an itinerary.

**Response:**
```json
{
  "success": true,
  "data": {
    "_id": "507f191e810c19729de860ea",
    "tour_name": "10-Day Kenya Safari",
    "client_group": "Smith Family",
    "dates": "Jan 15-25, 2025",
    "duration": "10 days / 9 nights",
    "days": 10,
    "countries": ["Kenya"],
    "scraped_at": "2025-12-02T10:30:00Z"
  }
}
```

---

### GET /api/itinerary/:doc_id/daily

Get daily summaries for an itinerary.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "day": 1,
      "date": "2025-01-15",
      "location": "Nairobi",
      "accommodation": "Giraffe Manor",
      "activities_count": 2
    },
    /* ... more days ... */
  ]
}
```

---

### GET /api/itinerary/list

List all itineraries with pagination and search.

**Query Parameters:**
- `page` (number, optional) - Page number (default: `1`)
- `per_page` (number, optional) - Items per page (default: `20`)
- `search` (string, optional) - Full-text search query
- `sort_by` (string, optional) - Field to sort by (default: `_metadata.scraped_at`)
- `sort_order` (string, optional) - `asc` or `desc` (default: `desc`)

**Example:**
```bash
GET /api/itinerary/list?page=1&per_page=20&search=Kenya&sort_order=desc
```

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [ /* array of itinerary summaries */ ],
    "pagination": {
      "total": 45,
      "page": 1,
      "per_page": 20,
      "pages": 3
    }
  }
}
```

---

### PUT /api/itinerary/:doc_id/deactivate

Deactivate an itinerary (soft delete). The itinerary will be hidden from normal queries but remains in the database.

**URL Parameters:**
- `doc_id` (string, required) - MongoDB ObjectId of the itinerary

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Itinerary deactivated successfully"
  }
}
```

---

### DELETE /api/itinerary/:doc_id

Permanently delete an itinerary from the database.

⚠️ **Warning:** This action cannot be undone. Consider using deactivate instead.

**URL Parameters:**
- `doc_id` (string, required) - MongoDB ObjectId of the itinerary

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Itinerary deleted successfully"
  }
}
```

---

### GET /api/itinerary/search

Search itineraries by tour name or client group.

**Query Parameters:**
- `q` (string, required) - Search query
- `type` (string, optional) - Search type: `tour`, `client`, or `all` (default: `all`)

**Example:**
```bash
GET /api/itinerary/search?q=Kenya&type=tour
```

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [ /* array of matching itineraries */ ],
    "total": 12
  }
}
```

---

## Itinerary Types

Supported itinerary types (you can use any string value):

| Type | Description |
|------|-------------|
| `option_1` | First itinerary option (default) |
| `option_2` | Second itinerary option |
| `option_3` | Third itinerary option |
| `extension` | Trip extension |
| `final` | Final confirmed itinerary |
| `revised` | Revised version |
| `custom` | Custom type |

---

## Error Responses

All endpoints follow this error format:

```json
{
  "success": false,
  "error": "Error message description",
  "status": 400
}
```

Common HTTP status codes:
- `400` - Bad Request (missing required fields)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `500` - Internal Server Error

---

## Authentication

All endpoints require authentication via JWT token in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

---

## Common Workflows

### Workflow 1: Create Multiple Itinerary Options

```bash
# Create Option 1
POST /api/itinerary/create
{
  "url": "...",
  "booking_id": "507f1f77bcf86cd799439011",
  "itinerary_type": "option_1"
}

# Create Option 2
POST /api/itinerary/create
{
  "url": "...",
  "booking_id": "507f1f77bcf86cd799439011",
  "itinerary_type": "option_2"
}

# Retrieve both options
GET /api/bookings/507f1f77bcf86cd799439011/itineraries
```

### Workflow 2: Revise an Itinerary

```bash
# Create revised version
POST /api/itinerary/create
{
  "url": "...",
  "booking_id": "507f1f77bcf86cd799439011",
  "itinerary_type": "option_1",
  "version": 2
}

# Deactivate old version
PUT /api/itinerary/<old_doc_id>/deactivate

# Get latest version
GET /api/bookings/507f1f77bcf86cd799439011/itineraries?type=option_1
# Returns version 2 (highest version number)
```

### Workflow 3: Add Extension to Booking

```bash
# Create extension itinerary
POST /api/itinerary/create
{
  "url": "...",
  "booking_id": "507f1f77bcf86cd799439011",
  "itinerary_type": "extension"
}

# Get all itineraries (main + extension)
GET /api/bookings/507f1f77bcf86cd799439011/itineraries
```
