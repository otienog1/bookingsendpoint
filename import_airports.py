"""
Script to import airports from airports.json into MongoDB
Run this once to populate the airports collection
"""
import json
import os
from app import create_app
from app.mongodb_models import Airport

def import_airports():
    """Import airports from JSON file to MongoDB"""
    app = create_app()

    with app.app_context():
        # Path to airports.json
        json_path = os.path.join(os.path.dirname(__file__), 'app', 'scraper', 'airports.json')

        print(f"Loading airports from: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            airports_data = json.load(f)

        print(f"Found {len(airports_data)} airports to import")

        # Clear existing airports (optional - comment out if you want to keep existing data)
        print("Clearing existing airports...")
        Airport.get_collection().delete_many({})

        # Import airports
        imported = 0
        skipped = 0
        errors = 0

        for airport in airports_data:
            try:
                # Extract geolocation if present
                latitude = None
                longitude = None
                if '_geoloc' in airport:
                    latitude = airport['_geoloc'].get('lat')
                    longitude = airport['_geoloc'].get('lng')

                # Check if airport already exists
                existing = Airport.find_by_iata(airport['iata_code'])
                if existing:
                    skipped += 1
                    continue

                # Create airport
                Airport.create_airport(
                    name=airport['name'],
                    city=airport['city'],
                    country=airport['country'],
                    iata_code=airport['iata_code'],
                    latitude=latitude,
                    longitude=longitude,
                    links_count=airport.get('links_count', 0)
                )
                imported += 1

                if imported % 100 == 0:
                    print(f"Imported {imported} airports...")

            except Exception as e:
                print(f"Error importing airport {airport.get('iata_code', 'UNKNOWN')}: {str(e)}")
                errors += 1

        print(f"\n=== Import Complete ===")
        print(f"✓ Imported: {imported}")
        print(f"⊘ Skipped: {skipped}")
        print(f"✗ Errors: {errors}")
        print(f"Total in database: {Airport.get_collection().count_documents({})}")

        # Create index on iata_code for faster lookups
        print("\nCreating index on iata_code...")
        Airport.get_collection().create_index("iata_code", unique=True)
        Airport.get_collection().create_index("country")
        Airport.get_collection().create_index("city")
        print("✓ Indexes created")

if __name__ == "__main__":
    import_airports()
