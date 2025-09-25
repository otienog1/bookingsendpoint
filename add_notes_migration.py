#!/usr/bin/env python3
"""
Migration script to add notes field to bookings table
Run this script to add the notes column to existing SQL bookings table
"""

import os
import sys
from sqlalchemy import create_engine, text, Column, Text, MetaData, Table
from sqlalchemy.exc import OperationalError, ProgrammingError

def get_database_url():
    """Get database URL from environment or use default"""
    return os.getenv('DATABASE_URL', 'sqlite:///bookings.db')

def add_notes_column():
    """Add notes column to bookings table if it doesn't exist"""
    database_url = get_database_url()
    print(f"Connecting to database: {database_url}")
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if notes column already exists
            try:
                result = conn.execute(text("SELECT notes FROM bookings LIMIT 1"))
                print("Notes column already exists in bookings table.")
                return True
            except (OperationalError, ProgrammingError):
                # Column doesn't exist, need to add it
                print("Notes column doesn't exist. Adding it now...")
                pass
            
            # Add the notes column
            try:
                if 'sqlite' in database_url.lower():
                    # SQLite syntax
                    conn.execute(text("ALTER TABLE bookings ADD COLUMN notes TEXT"))
                elif 'postgresql' in database_url.lower():
                    # PostgreSQL syntax
                    conn.execute(text("ALTER TABLE bookings ADD COLUMN notes TEXT"))
                elif 'mysql' in database_url.lower():
                    # MySQL syntax
                    conn.execute(text("ALTER TABLE bookings ADD COLUMN notes TEXT"))
                else:
                    # Generic SQL - should work for most databases
                    conn.execute(text("ALTER TABLE bookings ADD COLUMN notes TEXT"))
                
                conn.commit()
                print("Successfully added notes column to bookings table.")
                return True
                
            except Exception as e:
                print(f"Error adding notes column: {str(e)}")
                conn.rollback()
                return False
                
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return False

def verify_migration():
    """Verify that the migration was successful"""
    database_url = get_database_url()
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Try to select from the notes column
            result = conn.execute(text("SELECT id, notes FROM bookings LIMIT 1"))
            print("Migration verification successful - notes column is accessible.")
            return True
            
    except Exception as e:
        print(f"Migration verification failed: {str(e)}")
        return False

def main():
    """Main migration function"""
    print("Starting migration to add notes column to bookings table...")
    
    # Add the column
    if add_notes_column():
        # Verify the migration
        if verify_migration():
            print("Migration completed successfully!")
            return 0
        else:
            print("Migration verification failed!")
            return 1
    else:
        print("Migration failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())