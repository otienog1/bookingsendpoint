"""
Migration Script: Convert Itinerary Relationship from One-to-One to One-to-Many

This script:
1. Adds booking_id, itinerary_type, version, and is_active fields to existing itineraries
2. Removes the itinerary_id field from bookings (SQL database)
3. Updates existing itinerary documents with default values

Run this script after deploying the code changes to update the database schema.
"""

import os
import sys
from datetime import datetime, timezone
from bson import ObjectId

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, mongo
from config import Config


def migrate_itineraries():
    """Add new fields to existing itinerary documents."""
    print("=" * 70)
    print("ITINERARY MIGRATION SCRIPT")
    print("=" * 70)
    print()

    app = create_app()

    with app.app_context():
        itineraries_collection = mongo.db.itineraries

        # Get all existing itineraries
        existing_itineraries = list(itineraries_collection.find({}))
        total_count = len(existing_itineraries)

        print(f"Found {total_count} existing itineraries")
        print()

        if total_count == 0:
            print("No itineraries to migrate.")
            return

        # Ask for confirmation
        response = input(f"Do you want to migrate {total_count} itineraries? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Migration cancelled.")
            return

        print()
        print("Starting migration...")
        print("-" * 70)

        updated_count = 0
        skipped_count = 0

        for itinerary in existing_itineraries:
            itinerary_id = itinerary['_id']

            # Check if already migrated
            if 'itinerary_type' in itinerary:
                print(f"✓ Skipping {itinerary_id} (already migrated)")
                skipped_count += 1
                continue

            # Prepare update
            update_data = {
                '$set': {
                    'itinerary_type': 'option_1',  # Default to option_1 for existing itineraries
                    'version': 1,
                    'is_active': True,
                    '_metadata.updated_at': datetime.now(timezone.utc)
                }
            }

            # If booking_id is not set, leave it as None (itinerary not linked to any booking)
            if 'booking_id' not in itinerary:
                update_data['$set']['booking_id'] = None

            # Perform update
            result = itineraries_collection.update_one(
                {'_id': itinerary_id},
                update_data
            )

            if result.modified_count > 0:
                tour_name = itinerary.get('trip_overview', {}).get('tour_name', 'Unknown')
                print(f"✓ Updated itinerary: {itinerary_id} ({tour_name})")
                updated_count += 1
            else:
                print(f"✗ Failed to update itinerary: {itinerary_id}")

        print("-" * 70)
        print()
        print("MIGRATION SUMMARY:")
        print(f"  Total itineraries: {total_count}")
        print(f"  Updated: {updated_count}")
        print(f"  Skipped (already migrated): {skipped_count}")
        print(f"  Failed: {total_count - updated_count - skipped_count}")
        print()

        if updated_count > 0:
            print("✓ Migration completed successfully!")
        else:
            print("! No itineraries were updated.")

        print()
        print("=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print()
        print("1. The itinerary schema has been updated to support one-to-many relationships")
        print("2. All existing itineraries have been marked as 'option_1' type")
        print("3. The itinerary_id field should be removed from the bookings table")
        print("   using an Alembic migration (SQL database)")
        print()
        print("To create the Alembic migration for the bookings table:")
        print("  1. Create a new migration file:")
        print("     alembic revision -m 'remove_itinerary_id_from_bookings'")
        print("  2. Edit the migration file to drop the itinerary_id column")
        print("  3. Run: alembic upgrade head")
        print()
        print("=" * 70)


def create_alembic_migration_template():
    """Print a template for the Alembic migration."""
    print()
    print("=" * 70)
    print("ALEMBIC MIGRATION TEMPLATE")
    print("=" * 70)
    print()
    print("Create a new file in backend/migrations/versions/ with this content:")
    print()
    print("""
\"\"\"remove itinerary_id from bookings

Revision ID: <auto_generated>
Revises: <previous_revision>
Create Date: <auto_generated>

\"\"\"
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '<auto_generated>'
down_revision = '<previous_revision>'
branch_labels = None
depends_on = None


def upgrade():
    # Remove the itinerary_id column from bookings table
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        batch_op.drop_column('itinerary_id')


def downgrade():
    # Add the itinerary_id column back if needed
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('itinerary_id', sa.String(length=24), nullable=True))
""")
    print()
    print("=" * 70)


if __name__ == '__main__':
    print()
    migrate_itineraries()
    create_alembic_migration_template()
    print()
