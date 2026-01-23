"""Check accommodation nights discrepancies"""
from app import create_app
from app import mongo
from bson import ObjectId
import json

app = create_app()
with app.app_context():
    # Get the itinerary
    itin = mongo.db.itineraries.find_one({'_id': ObjectId('6936cb9aa3fd23b2799fac2f')})

    # Get accommodations
    accommodations = itin.get('inclusions', {}).get('accommodation', [])

    print('=== INCLUSIONS ACCOMMODATIONS ===')
    for i, acc in enumerate(accommodations, 1):
        print(f'{i}. {acc.get("name")} - {acc.get("nights")} nights - {acc.get("basis")}')

    print('\n=== DAILY ITINERARY ===')
    daily = itin.get('daily_itinerary', [])
    print(f'Total days: {len(daily)}')

    # Count nights per property from daily itinerary
    property_nights = {}
    for day in daily:
        acc_name = day.get('accommodation', {}).get('name')
        if acc_name and acc_name != 'N/A':
            if acc_name not in property_nights:
                property_nights[acc_name] = 0
            property_nights[acc_name] += 1

    print('\nActual nights per property (from daily itinerary):')
    for prop, nights in sorted(property_nights.items()):
        print(f'  {prop}: {nights} nights')

    # Compare
    print('\n=== COMPARISON ===')
    incl_dict = {acc.get('name'): acc.get('nights') for acc in accommodations}

    for prop in sorted(set(list(incl_dict.keys()) + list(property_nights.keys()))):
        incl_nights = incl_dict.get(prop, 0)
        actual_nights = property_nights.get(prop, 0)

        if incl_nights != actual_nights:
            print(f'MISMATCH: {prop}')
            print(f'  Inclusions says: {incl_nights} nights')
            print(f'  Daily itinerary has: {actual_nights} nights')
            print(f'  Difference: {incl_nights - actual_nights}')
        else:
            print(f'OK: {prop} - {incl_nights} nights')
