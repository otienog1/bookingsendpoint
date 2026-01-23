"""Debug script to check itinerary-booking relationships"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, mongo
from bson import ObjectId

app = create_app()

with app.app_context():
    # Get all itineraries
    itineraries = list(mongo.db.itineraries.find({}))

    print(f"\n{'='*70}")
    print(f"TOTAL ITINERARIES: {len(itineraries)}")
    print(f"{'='*70}\n")

    for idx, itin in enumerate(itineraries, 1):
        print(f"{idx}. Itinerary ID: {itin['_id']}")
        print(f"   Tour Name: {itin.get('trip_overview', {}).get('tour_name', 'N/A')}")
        print(f"   Booking ID: {itin.get('booking_id', 'NOT SET')}")
        print(f"   Itinerary Type: {itin.get('itinerary_type', 'NOT SET')}")
        print(f"   Is Active: {itin.get('is_active', 'NOT SET')}")
        print()

    # Test the query for a specific booking
    test_booking_id = "690859b7d8497c4dc28281a3"
    print(f"\n{'='*70}")
    print(f"TESTING QUERY FOR BOOKING: {test_booking_id}")
    print(f"{'='*70}\n")

    # Try different query variations
    queries = [
        {"booking_id": ObjectId(test_booking_id)},
        {"booking_id": test_booking_id},
        {"booking_id": {"$exists": True}},
    ]

    for idx, query in enumerate(queries, 1):
        results = list(mongo.db.itineraries.find(query))
        print(f"Query {idx}: {query}")
        print(f"Results: {len(results)} itineraries found")
        for r in results:
            print(f"  - {r['_id']}: booking_id={r.get('booking_id')}, type={type(r.get('booking_id'))}")
        print()
