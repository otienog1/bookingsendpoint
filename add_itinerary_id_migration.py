"""
Migration script to add itinerary_id column to bookings table.

Usage:
    python add_itinerary_id_migration.py

Or from Flask shell:
    flask shell
    >>> from add_itinerary_id_migration import add_itinerary_id_column
    >>> add_itinerary_id_column()
"""
from sqlalchemy import text
from app import create_app, db

def add_itinerary_id_column():
    """
    Add itinerary_id column to bookings table if it doesn't exist.
    """
    app = create_app()

    with app.app_context():
        connection = db.engine.connect()

        try:
            # Check if column already exists
            result = connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='bookings' AND column_name='itinerary_id'"
            ))

            if result.fetchone():
                print("itinerary_id column already exists in bookings table")
                return

            # Add the itinerary_id column
            connection.execute(text(
                "ALTER TABLE bookings ADD COLUMN itinerary_id VARCHAR(24)"
            ))
            connection.commit()

            print("Successfully added itinerary_id column to bookings table")

        except Exception as e:
            connection.rollback()
            print(f"Migration failed: {str(e)}")
            raise
        finally:
            connection.close()


if __name__ == "__main__":
    add_itinerary_id_column()
