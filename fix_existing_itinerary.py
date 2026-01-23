"""Fix existing itinerary by adding required fields"""

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, mongo

app = create_app()

with app.app_context():
    # Get all itineraries without the new fields
    itineraries = list(mongo.db.itineraries.find({
        "$or": [
            {"itinerary_type": {"$exists": False}},
            {"version": {"$exists": False}},
            {"is_active": {"$exists": False}}
        ]
    }))

    print(f"\nFound {len(itineraries)} itineraries to migrate\n")

    for itin in itineraries:
        itin_id = itin['_id']
        tour_name = itin.get('trip_overview', {}).get('tour_name', 'Unknown')

        print(f"Updating itinerary {itin_id}: {tour_name}")

        # Update with default values
        update_data = {
            '$set': {
                'booking_id': None,  # Not linked to any booking
                'itinerary_type': 'option_1',
                'version': 1,
                'is_active': True,
                '_metadata.updated_at': datetime.now(timezone.utc)
            }
        }

        result = mongo.db.itineraries.update_one(
            {'_id': itin_id},
            update_data
        )

        if result.modified_count > 0:
            print(f"  [OK] Successfully updated\n")
        else:
            print(f"  [FAIL] Failed to update\n")

    print("Migration completed!")

    # Verify the results
    print("\n" + "="*70)
    print("VERIFICATION")
    print("="*70 + "\n")

    all_itineraries = list(mongo.db.itineraries.find({}))
    for itin in all_itineraries:
        print(f"Itinerary {itin['_id']}:")
        print(f"  booking_id: {itin.get('booking_id', 'NOT SET')}")
        print(f"  itinerary_type: {itin.get('itinerary_type', 'NOT SET')}")
        print(f"  version: {itin.get('version', 'NOT SET')}")
        print(f"  is_active: {itin.get('is_active', 'NOT SET')}")
        print()
