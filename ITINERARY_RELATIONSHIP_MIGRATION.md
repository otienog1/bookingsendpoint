# Itinerary-Booking Relationship Migration

## Overview

This document describes the migration from a **one-to-one** relationship to a **one-to-many** relationship between bookings and itineraries.

### Previous Design (One-to-One)
- Each booking could reference **one** itinerary via `itinerary_id` field
- Itineraries had no reference back to bookings
- Limited flexibility for handling multiple itinerary options or extensions

### New Design (One-to-Many)
- Each booking can have **multiple** itineraries
- Itineraries reference their parent booking via `booking_id` field
- Supports different itinerary types: options, extensions, revisions
- Enables version tracking and soft-delete (active/inactive)

---

## Changes Made

### 1. Itinerary Schema Updates

**New fields added to itinerary documents:**

```python
{
    'booking_id': ObjectId,      # Reference to parent booking
    'itinerary_type': str,       # Type: 'option_1', 'option_2', 'extension', 'final', etc.
    'version': int,              # Version number for tracking revisions (1, 2, 3...)
    'is_active': bool,           # Whether this itinerary is active/valid
    # ... existing fields ...
}
```

**New MongoDB indexes:**
- `booking_id_idx` - Fast lookup by booking
- `booking_type_idx` - Compound index for booking + type queries
- `booking_active_idx` - Find active itineraries for a booking

### 2. New Model Methods

**Added to `ItineraryModel`:**

- `find_by_booking(booking_id, active_only=True)` - Get all itineraries for a booking
- `find_by_booking_and_type(booking_id, itinerary_type, active_only=True)` - Get specific type
- `deactivate_itinerary(doc_id)` - Soft delete an itinerary

**Updated methods:**

- `create()` - Now accepts `booking_id`, `itinerary_type`, and `version` parameters

### 3. New API Endpoints

**GET `/api/scraper/bookings/<booking_id>/itineraries`**
- Fetches all itineraries for a specific booking
- Query params:
  - `active_only=true` - Only return active itineraries (default)
  - `type=option_1` - Filter by itinerary type

**PUT `/api/scraper/itineraries/<doc_id>/deactivate`**
- Deactivate an itinerary (soft delete)

**Updated endpoint:**

**POST `/api/scraper/scrape`**
- Now accepts additional parameters:
  - `booking_id` - Link itinerary to a booking
  - `itinerary_type` - Type of itinerary (default: 'option_1')
  - `version` - Version number (default: 1)

### 4. Booking Model Updates

**Removed from `Booking` class:**
- `itinerary_id` field (SQL column)
- `itinerary_id` from `to_dict()` method

**Note:** Bookings no longer store itinerary references. To get itineraries for a booking, use the new API endpoint.

---

## Migration Instructions

### Step 1: Update Code (Already Done)
✓ Code changes have been applied to:
- [itinerary_model.py](backend/app/scraper/itinerary_model.py)
- [scraperbp.py](backend/app/scraper/scraperbp.py)
- [booking.py](backend/app/booking.py)

### Step 2: Migrate MongoDB Itineraries

Run the migration script to update existing itinerary documents:

```bash
cd backend
python migrate_itinerary_relationship.py
```

This script will:
- Add `itinerary_type`, `version`, and `is_active` to all existing itineraries
- Set default values (`option_1`, version `1`, active `true`)
- Leave `booking_id` as `null` for unlinked itineraries

### Step 3: Migrate SQL Database (Bookings Table)

Run the Alembic migration to remove `itinerary_id` column:

```bash
cd backend
alembic upgrade head
```

This will execute the migration in [remove_itinerary_id_from_bookings.py](migrations/versions/remove_itinerary_id_from_bookings.py).

---

## API Endpoints

### Itinerary Management

All itinerary-specific endpoints are under `/api/itinerary`:

#### Create Itinerary
```bash
POST /api/itinerary/create
{
  "url": "https://portal.example.com/itinerary/123",
  "booking_id": "507f1f77bcf86cd799439011",  // Required
  "itinerary_type": "option_1",  // Default: 'option_1'
  "version": 1,  // Default: 1
  "headless": true  // Optional, default: true
}
```

#### Get Single Itinerary
```bash
GET /api/itinerary/<doc_id>
```

#### Get Itinerary Summary
```bash
GET /api/itinerary/<doc_id>/summary
```

#### Get Daily Breakdown
```bash
GET /api/itinerary/<doc_id>/daily
```

#### List All Itineraries
```bash
GET /api/itinerary/list?page=1&per_page=20&search=safari
```

#### Deactivate Itinerary (Soft Delete)
```bash
PUT /api/itinerary/<doc_id>/deactivate
```

#### Delete Itinerary (Permanent)
```bash
DELETE /api/itinerary/<doc_id>
```

### Booking-Related Endpoints

Booking-related endpoints are under `/api/bookings`:

#### Get All Itineraries for a Booking
```bash
GET /api/bookings/<booking_id>/itineraries
```

**Query Parameters:**
- `active_only=true` - Only return active itineraries (default: true)
- `type=option_1` - Filter by specific itinerary type

**Examples:**

Get all active itineraries:
```bash
GET /api/bookings/507f1f77bcf86cd799439011/itineraries
```

Get specific itinerary type:
```bash
GET /api/bookings/507f1f77bcf86cd799439011/itineraries?type=option_1
```

Get all itineraries (including inactive):
```bash
GET /api/bookings/507f1f77bcf86cd799439011/itineraries?active_only=false
```

---

## Usage Examples

### Creating an Itinerary Linked to a Booking

**Option 1 - Main Itinerary:**
```bash
POST /api/itinerary/create
{
  "url": "https://portal.example.com/itinerary/123",
  "booking_id": "507f1f77bcf86cd799439011",
  "itinerary_type": "option_1"
}
```

**Option 2 - Alternative Itinerary:**
```bash
POST /api/itinerary/create
{
  "url": "https://portal.example.com/itinerary/456",
  "booking_id": "507f1f77bcf86cd799439011",
  "itinerary_type": "option_2"
}
```

**Extension Itinerary:**
```bash
POST /api/itinerary/create
{
  "url": "https://portal.example.com/itinerary/789",
  "booking_id": "507f1f77bcf86cd799439011",
  "itinerary_type": "extension"
}
```

### Fetching Itineraries for a Booking

**Get all active itineraries:**
```bash
GET /api/bookings/507f1f77bcf86cd799439011/itineraries
```

**Get specific itinerary type:**
```bash
GET /api/bookings/507f1f77bcf86cd799439011/itineraries?type=option_1
```

**Get all itineraries (including inactive):**
```bash
GET /api/bookings/507f1f77bcf86cd799439011/itineraries?active_only=false
```

### Deactivating an Itinerary

```bash
PUT /api/itinerary/507f191e810c19729de860ea/deactivate
```

---

## Itinerary Types

The system supports various itinerary types to handle different scenarios:

| Type | Description | Use Case |
|------|-------------|----------|
| `option_1` | First itinerary option | Main/primary itinerary proposal |
| `option_2` | Second itinerary option | Alternative itinerary for client choice |
| `option_3` | Third itinerary option | Additional alternative |
| `extension` | Trip extension | Add-on days/activities to existing booking |
| `final` | Final confirmed itinerary | The chosen/confirmed version |
| `revised` | Revised version | Updated version after client feedback |
| `custom` | Custom type | For special cases |

You can use any string value for `itinerary_type` - these are just recommended conventions.

---

## Version Tracking

Each itinerary has a `version` number (integer) that can be incremented for revisions:

**Example: Revising an itinerary**

1. Create initial itinerary:
   ```json
   {"itinerary_type": "option_1", "version": 1}
   ```

2. Create revised version:
   ```json
   {"itinerary_type": "option_1", "version": 2}
   ```

3. Optionally deactivate old version:
   ```bash
   PUT /api/scraper/itineraries/<old_doc_id>/deactivate
   ```

The `find_by_booking_and_type()` method automatically returns the latest version (highest version number).

---

## Benefits of This Design

1. **Flexibility**: Handle multiple itinerary options, extensions, and revisions
2. **Clean Separation**: Itineraries are in MongoDB, bookings in SQL
3. **Scalability**: No limit on itineraries per booking
4. **Version Control**: Track itinerary revisions over time
5. **Soft Delete**: Deactivate instead of delete for audit trail
6. **Type Safety**: Clearly identify purpose of each itinerary

---

## Backward Compatibility

⚠️ **Breaking Changes:**

- The `itinerary_id` field is removed from bookings
- Existing integrations that relied on `booking.itinerary_id` must be updated to use the new API

**Migration Path:**

If you have existing code that uses `booking.itinerary_id`, replace it with:

```python
# Old code:
itinerary_id = booking.itinerary_id

# New code:
from app.scraper.itinerary_model import ItineraryModel
model = ItineraryModel(mongo)
itineraries = model.find_by_booking(booking.id, active_only=True)
```

---

## Testing

After migration, verify:

1. ✓ Existing itineraries have new fields
2. ✓ New itineraries can be created with booking links
3. ✓ Booking queries work correctly
4. ✓ Itinerary type filtering works
5. ✓ Deactivation works as expected
6. ✓ The `itinerary_id` column is removed from bookings table

---

## Rollback

If you need to rollback:

**MongoDB:**
- Manually remove the new fields from itinerary documents

**SQL Database:**
```bash
alembic downgrade -1
```

This will restore the `itinerary_id` column to the bookings table.

---

## Questions or Issues?

Contact the development team or refer to:
- [Itinerary Model](backend/app/scraper/itinerary_model.py)
- [API Blueprint](backend/app/scraper/scraperbp.py)
- [Migration Script](backend/migrate_itinerary_relationship.py)
