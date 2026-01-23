# Airport Data Setup Guide

This document explains how airport data is used in the bookings system.

## Architecture Overview

The system uses a **hybrid approach** for airport data:

1. **JSON File** (`app/scraper/airports.json`) - Used by the LLM scraper for best performance
2. **MongoDB Collection** (`airports`) - Used by the rest of the application for queries and API endpoints

## Setup Instructions

### 1. Import Airports to MongoDB

Run the import script to populate the MongoDB collection with airport data:

```bash
cd backend
python import_airports.py
```

This will:
- Load all airports from `app/scraper/airports.json`
- Import them into the `airports` MongoDB collection
- Create indexes on `iata_code`, `country`, and `city` for fast lookups
- Display import statistics

### 2. Verify Import

Check that airports were imported successfully:

```python
from app.mongodb_models import Airport

# Get total count
print(f"Total airports: {Airport.get_collection().count_documents({})}")

# Test searching
jnb = Airport.find_by_iata("JNB")
print(f"Found: {jnb['name']}, {jnb['city']}, {jnb['country']}")

# Search by country
kenya_airports = Airport.find_by_country("Kenya")
print(f"Kenya has {len(kenya_airports)} airports")
```

## How It Works

### In the Scraper

The `ItineraryScraper` class:

1. **Loads airports on initialization** from `airports.json` (3315 airports worldwide)
2. **Extracts countries** from the raw itinerary data dynamically
3. **Filters relevant airports** based on:
   - Airports in mentioned countries (automatically detected)
   - Major international hubs globally (Europe, Middle East, Asia Pacific, North America, Africa, South America)
   - Top 30 by `links_count` to avoid token overflow (reduced for prompt optimization)
4. **Adds airport reference** to the LLM prompt dynamically

Example of what the LLM sees (adapts to each itinerary):

```
⚠️ AIRPORT REFERENCE DATABASE ⚠️
Use these airports for accurate extraction:
[Airport codes and details relevant to THIS specific itinerary's countries]
[Plus major international hubs for connections]
...
```

**The system is fully generic** - it works for ANY destination worldwide, not just specific regions.

### In the Application

The `Airport` MongoDB model provides methods for:

```python
# Find by IATA code
Airport.find_by_iata("JNB")

# Find by country
Airport.find_by_country("South Africa")

# Find by city
Airport.find_by_city("Nairobi")

# Search across all fields
Airport.search("heathrow")

# Get all airports
Airport.get_all()
```

## Benefits of Hybrid Approach

### Why JSON for Scraper?
✅ **Fast** - No database queries during scraping
✅ **Self-contained** - Works even if MongoDB is down
✅ **Efficient** - Loaded once at initialization
✅ **Better LLM accuracy** - Direct context in prompt

### Why Database for Application?
✅ **Queryable** - Search and filter capabilities
✅ **API-ready** - Easy to build endpoints
✅ **User-editable** - Can add/update airports
✅ **Relational** - Can link to bookings/itineraries

## API Endpoint Examples

You can create API endpoints to use airport data:

```python
# In bookingsbp.py or new airportsbp.py

@app.route("/api/airports/search", methods=["GET"])
def search_airports():
    query = request.args.get("q", "")
    airports = Airport.search(query)
    return jsonify({"airports": [Airport.to_dict(a) for a in airports]})

@app.route("/api/airports/country/<country>", methods=["GET"])
def get_airports_by_country(country):
    airports = Airport.find_by_country(country)
    return jsonify({"airports": [Airport.to_dict(a) for a in airports]})

@app.route("/api/airports/<iata_code>", methods=["GET"])
def get_airport(iata_code):
    airport = Airport.find_by_iata(iata_code.upper())
    if not airport:
        return jsonify({"error": "Airport not found"}), 404
    return jsonify({"airport": Airport.to_dict(airport)})
```

## Data Structure

Each airport document contains:

```json
{
  "iata_code": "JNB",
  "name": "OR Tambo International Airport",
  "city": "Johannesburg",
  "country": "South Africa",
  "latitude": -26.1392,
  "longitude": 28.246,
  "links_count": 890,
  "created_at": "2025-01-07T10:30:00Z",
  "updated_at": "2025-01-07T10:30:00Z"
}
```

## Updating Airport Data

### To update the JSON file:
1. Edit `frontend/airports.json` (master source)
2. Copy to backend: `cp frontend/airports.json backend/app/scraper/airports.json`
3. Restart the scraper service

### To update MongoDB:
1. Re-run the import script: `python import_airports.py`
2. Or manually update via the Airport model:

```python
from app.mongodb_models import Airport

# Add new airport
Airport.create_airport(
    name="New Airport",
    city="City Name",
    country="Country Name",
    iata_code="XYZ",
    latitude=-1.234,
    longitude=56.789
)

# Update existing
Airport.update_one(
    {"iata_code": "JNB"},
    {"$set": {"name": "Updated Name"}}
)
```

## Performance Considerations

- **Scraper**: Loads 3315 airports worldwide at startup (< 1s)
- **Filtering**: Dynamically reduces to ~30 most relevant airports per itinerary based on mentioned countries
- **Token usage**: ~500-800 tokens for airport reference (optimized for LLM prompt limits)
- **MongoDB**: Indexed queries return in milliseconds
- **Scalability**: Works for any destination globally - safari tours, city breaks, beach holidays, multi-country trips, etc.

## Troubleshooting

### Airports not loading in scraper?
```bash
# Check if file exists
ls backend/app/scraper/airports.json

# Check scraper output
# Should see: "✓ Loaded 3315 airports for reference"
```

### MongoDB import failing?
```bash
# Ensure MongoDB is running
# Check connection string in .env
MONGODB_URI=mongodb://localhost:27017/bookings

# Run with error output
python import_airports.py
```

### LLM still missing airports?
- Check the filtered countries extraction logic
- Verify airport reference is in prompt
- Ensure airport has correct country name (case-sensitive)

## Files

- `frontend/airports.json` - Master source file
- `backend/app/scraper/airports.json` - Copy used by scraper
- `backend/app/mongodb_models.py` - Airport model definition
- `backend/import_airports.py` - Import script
- `backend/AIRPORTS_SETUP.md` - This file
