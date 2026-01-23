"""Link itinerary to booking"""
from app import create_app
from app import mongo
from bson import ObjectId

app = create_app()
with app.app_context():
    # Update the itinerary with the booking_id
    result = mongo.db.itineraries.update_one(
        {'_id': ObjectId('6936cb9aa3fd23b2799fac2f')},
        {
            '$set': {
                'booking_id': ObjectId('690859b7d8497c4dc28281a3'),
                'itinerary_type': 'option_1',
                'is_active': True
            }
        }
    )
    print(f'Updated {result.modified_count} document(s)')

    # Verify
    itin = mongo.db.itineraries.find_one(
        {'_id': ObjectId('6936cb9aa3fd23b2799fac2f')},
        {'booking_id': 1, 'itinerary_type': 1, 'is_active': 1}
    )
    print(f'Verification:')
    print(f'  Booking ID: {itin.get("booking_id")}')
    print(f'  Type: {itin.get("itinerary_type")}')
    print(f'  Active: {itin.get("is_active")}')
