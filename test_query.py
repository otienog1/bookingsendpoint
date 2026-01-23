"""Test the booking query"""

import sys
import os
from bson import ObjectId

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, mongo
from app.scraper.itinerary_model import ItineraryModel

app = create_app()

with app.app_context():
    model = ItineraryModel(mongo)

    test_booking_id = "690859b7d8497c4dc28281a3"

    print(f"\nTesting find_by_booking for booking_id: {test_booking_id}\n")

    # Test the model method
    results = model.find_by_booking(test_booking_id, active_only=True)

    print(f"Results found: {len(results)}")

    if results:
        for r in results:
            print(f"\nItinerary {r['_id']}:")
            print(f"  booking_id: {r.get('booking_id')}")
            print(f"  itinerary_type: {r.get('itinerary_type')}")
            print(f"  is_active: {r.get('is_active')}")
    else:
        print("\nNo itineraries found for this booking (CORRECT BEHAVIOR)")

    # Check all itineraries
    print(f"\n{'='*70}")
    print("ALL ITINERARIES IN DATABASE:")
    print(f"{'='*70}\n")

    all_itins = list(mongo.db.itineraries.find({}))
    for itin in all_itins:
        print(f"ID: {itin['_id']}")
        print(f"  booking_id: {itin.get('booking_id')} (type: {type(itin.get('booking_id'))})")
        print(f"  itinerary_type: {itin.get('itinerary_type')}")
        print(f"  is_active: {itin.get('is_active')}")
        print()
