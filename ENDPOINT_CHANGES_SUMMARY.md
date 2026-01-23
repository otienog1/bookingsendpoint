# API Endpoint Changes Summary

## Overview

The itinerary API endpoints have been restructured for better organization and clarity. The main changes are:

1. **Blueprint prefix changed**: `/api/scraper` → `/api/itinerary`
2. **Cleaner endpoint paths**: Removed redundant prefixes
3. **Booking-related endpoint moved**: Now under `/api/bookings` for consistency

---

## Endpoint Migration Map

### Old Endpoints → New Endpoints

| Old Endpoint | New Endpoint | Status |
|-------------|--------------|--------|
| `POST /api/scraper/scrape` | `POST /api/itinerary/create` | ✅ Updated |
| `GET /api/scraper/itineraries` | `GET /api/itinerary/list` | ✅ Updated |
| `GET /api/scraper/itineraries/<id>` | `GET /api/itinerary/<id>` | ✅ Updated |
| `GET /api/scraper/itineraries/<id>/summary` | `GET /api/itinerary/<id>/summary` | ✅ Updated |
| `GET /api/scraper/itineraries/<id>/daily` | `GET /api/itinerary/<id>/daily` | ✅ Updated |
| `DELETE /api/scraper/itineraries/<id>` | `DELETE /api/itinerary/<id>` | ✅ Updated |
| `PUT /api/scraper/itineraries/<id>/deactivate` | `PUT /api/itinerary/<id>/deactivate` | ✅ Updated |
| `GET /api/scraper/bookings/<id>/itineraries` | `GET /api/bookings/<id>/itineraries` | ✅ Moved |
| `GET /api/scraper/search` | `GET /api/itinerary/search` | ✅ Updated |

---

## New Endpoint Structure

### Itinerary Management (`/api/itinerary`)

```
POST   /api/itinerary/create              - Create new itinerary
GET    /api/itinerary/list                - List all itineraries
GET    /api/itinerary/<doc_id>            - Get single itinerary
GET    /api/itinerary/<doc_id>/summary    - Get itinerary summary
GET    /api/itinerary/<doc_id>/daily      - Get daily breakdown
PUT    /api/itinerary/<doc_id>/deactivate - Deactivate itinerary
DELETE /api/itinerary/<doc_id>            - Delete itinerary
GET    /api/itinerary/search              - Search itineraries
```

### Booking-Itinerary Relations (`/api/bookings`)

```
GET /api/bookings/<booking_id>/itineraries - Get all itineraries for booking
```

---

## Key Changes in Request/Response

### 1. Create Itinerary Endpoint

**Old:**
```bash
POST /api/scraper/scrape
```

**New:**
```bash
POST /api/itinerary/create
```

**Request body (unchanged):**
```json
{
  "url": "https://example.safariportal.app/itinerary/123",
  "booking_id": "507f1f77bcf86cd799439011",
  "itinerary_type": "option_1",
  "version": 1,
  "headless": true
}
```

### 2. Get Booking Itineraries

**Old:**
```bash
GET /api/scraper/bookings/507f1f77bcf86cd799439011/itineraries
```

**New:**
```bash
GET /api/bookings/507f1f77bcf86cd799439011/itineraries
```

This change makes the endpoint consistent with other booking-related endpoints like:
- `GET /api/bookings/<id>`
- `PUT /api/bookings/<id>`
- `DELETE /api/bookings/<id>`

---

## What You Need to Update

### Frontend Code

If you're using the frontend, update all API calls:

**Before:**
```javascript
// Old
fetch('/api/scraper/scrape', {
  method: 'POST',
  body: JSON.stringify({ url, booking_id })
})

// Old
fetch(`/api/scraper/bookings/${bookingId}/itineraries`)
```

**After:**
```javascript
// New
fetch('/api/itinerary/create', {
  method: 'POST',
  body: JSON.stringify({ url, booking_id })
})

// New
fetch(`/api/bookings/${bookingId}/itineraries`)
```

### API Clients

Update any API client libraries or wrappers to use the new endpoint paths.

### Documentation

Update any external documentation, Postman collections, or API specs to reflect the new endpoints.

---

## Backward Compatibility

⚠️ **Breaking Changes**: The old endpoints are no longer available. All clients must migrate to the new endpoints.

If you need backward compatibility temporarily, you can add route aliases in the blueprint file.

---

## Benefits of New Structure

1. **Clearer Organization**: `/api/itinerary` clearly indicates itinerary-specific endpoints
2. **Shorter URLs**: Removed redundant prefixes like `/itineraries/<id>`
3. **RESTful**: Better adherence to REST principles
4. **Consistency**: Booking-related endpoints grouped under `/api/bookings`
5. **Scalability**: Easier to add new endpoints without path conflicts

---

## Testing the New Endpoints

Use these curl commands to verify the new endpoints:

```bash
# Create itinerary
curl -X POST http://localhost:5000/api/itinerary/create \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.safariportal.app/itinerary/123",
    "booking_id": "507f1f77bcf86cd799439011",
    "itinerary_type": "option_1"
  }'

# Get booking itineraries
curl -X GET "http://localhost:5000/api/bookings/507f1f77bcf86cd799439011/itineraries" \
  -H "Authorization: Bearer YOUR_TOKEN"

# List all itineraries
curl -X GET "http://localhost:5000/api/itinerary/list?page=1&per_page=20" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get single itinerary
curl -X GET "http://localhost:5000/api/itinerary/507f191e810c19729de860ea" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Deactivate itinerary
curl -X PUT "http://localhost:5000/api/itinerary/507f191e810c19729de860ea/deactivate" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Files Modified

1. [scraperbp.py](backend/app/scraper/scraperbp.py)
   - Changed blueprint prefix from `/api/scraper` to `/api/itinerary`
   - Updated endpoint routes
   - Removed duplicate booking itineraries endpoint

2. [bookingsbp.py](backend/app/bookingsbp.py)
   - Added `GET /api/bookings/<booking_id>/itineraries` endpoint

3. [ITINERARY_RELATIONSHIP_MIGRATION.md](backend/ITINERARY_RELATIONSHIP_MIGRATION.md)
   - Updated documentation with new endpoints

4. [API_REFERENCE.md](backend/API_REFERENCE.md)
   - Complete API reference with new endpoints

---

## Questions?

- See [API_REFERENCE.md](API_REFERENCE.md) for detailed endpoint documentation
- See [ITINERARY_RELATIONSHIP_MIGRATION.md](ITINERARY_RELATIONSHIP_MIGRATION.md) for migration guide
- Check the source code for implementation details
