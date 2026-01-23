"""Link the orphaned itinerary to the correct booking"""

import sys
import os
from bson import ObjectId
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, mongo

app = create_app()

with app.app_context():
    # The itinerary ID and booking ID
    itinerary_id = "6926f6aa3449e032dc78e3c9"
    booking_id = "690859b7d8497c4dc28281a3"

    print(f"\n{'='*70}")
    print("LINKING ITINERARY TO BOOKING")
    print(f"{'='*70}\n")

    print(f"Itinerary ID: {itinerary_id}")
    print(f"Booking ID: {booking_id}\n")

    # Verify the itinerary exists
    itin = mongo.db.itineraries.find_one({'_id': ObjectId(itinerary_id)})
    if not itin:
        print(f"[ERROR] Itinerary {itinerary_id} not found!")
        sys.exit(1)

    print(f"Found itinerary: {itin.get('trip_overview', {}).get('tour_name', 'N/A')}")
    print(f"Current booking_id: {itin.get('booking_id')}\n")

    # Verify the booking exists
    booking = mongo.db.bookings.find_one({'_id': ObjectId(booking_id)})
    if not booking:
        print(f"[ERROR] Booking {booking_id} not found!")
        sys.exit(1)

    print(f"Found booking: {booking.get('client_name', 'N/A')}")
    print(f"Booking status: {booking.get('status', 'N/A')}\n")

    # Update the itinerary
    update_data = {
        '$set': {
            'booking_id': ObjectId(booking_id),
            '_metadata.updated_at': datetime.now(timezone.utc)
        }
    }

    result = mongo.db.itineraries.update_one(
        {'_id': ObjectId(itinerary_id)},
        update_data
    )

    if result.modified_count > 0:
        print(f"[OK] Successfully linked itinerary to booking!\n")
    else:
        print(f"[WARNING] No changes made (itinerary may already be linked)\n")

    # Verify the update
    print(f"{'='*70}")
    print("VERIFICATION")
    print(f"{'='*70}\n")

    updated_itin = mongo.db.itineraries.find_one({'_id': ObjectId(itinerary_id)})
    print(f"Itinerary ID: {updated_itin['_id']}")
    print(f"Tour Name: {updated_itin.get('trip_overview', {}).get('tour_name', 'N/A')}")
    print(f"Booking ID: {updated_itin.get('booking_id')}")
    print(f"Booking ID Type: {type(updated_itin.get('booking_id'))}")
    print(f"Itinerary Type: {updated_itin.get('itinerary_type')}")
    print(f"Version: {updated_itin.get('version')}")
    print(f"Is Active: {updated_itin.get('is_active')}\n")

    print(f"{'='*70}")
    print("Link complete!")
    print(f"{'='*70}\n")
