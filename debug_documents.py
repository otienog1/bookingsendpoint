#!/usr/bin/env python3
"""
Debug script to check document database contents
"""
import os
import sys
from bson import ObjectId
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, mongo

def debug_documents():
    """Debug function to check document database."""
    app = create_app()

    with app.app_context():
        try:
            booking_id = "68936016f55ded472bb0c745"
            print(f"=== Debugging Documents for Booking {booking_id} ===\n")

            # Check if booking exists
            print("1. Checking if booking exists...")
            booking = mongo.db.bookings.find_one({"_id": ObjectId(booking_id)})
            if booking:
                print(f"   [OK] Booking found: {booking.get('name', 'No name')}")
            else:
                print(f"   [ERROR] Booking not found with ID: {booking_id}")
                return

            # Check all documents for this booking (any category)
            print(f"\n2. Checking all documents for this booking...")
            all_docs = list(mongo.db.booking_documents.find({"booking_id": ObjectId(booking_id)}))
            print(f"   Found {len(all_docs)} total documents")

            if all_docs:
                for i, doc in enumerate(all_docs, 1):
                    print(f"   Document {i}:")
                    print(f"     - ID: {doc['_id']}")
                    print(f"     - Filename: {doc.get('filename', 'No filename')}")
                    print(f"     - Category: {doc.get('category', 'No category')}")
                    print(f"     - Size: {doc.get('size', 'No size')}")
                    print(f"     - Uploaded: {doc.get('uploaded_at', 'No date')}")

            # Check documents with specific categories
            print(f"\n3. Checking documents with 'Voucher' or 'Air Ticket' categories...")
            filtered_docs = list(mongo.db.booking_documents.find({
                "booking_id": ObjectId(booking_id),
                "category": {"$in": ["Voucher", "Air Ticket"]}
            }))
            print(f"   Found {len(filtered_docs)} matching documents")

            # Check what categories exist for this booking
            print(f"\n4. Checking what categories exist for this booking...")
            categories = mongo.db.booking_documents.distinct("category", {"booking_id": ObjectId(booking_id)})
            print(f"   Categories found: {categories}")

            # Check all documents in the database (to see if there are any at all)
            print(f"\n5. Checking total documents in database...")
            total_docs = mongo.db.booking_documents.count_documents({})
            print(f"   Total documents in database: {total_docs}")

            if total_docs > 0:
                print(f"\n6. Sample documents from database:")
                sample_docs = list(mongo.db.booking_documents.find().limit(3))
                for i, doc in enumerate(sample_docs, 1):
                    print(f"   Sample {i}:")
                    print(f"     - Booking ID: {doc.get('booking_id')}")
                    print(f"     - Filename: {doc.get('filename', 'No filename')}")
                    print(f"     - Category: {doc.get('category', 'No category')}")

        except Exception as e:
            print(f"Error during debugging: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_documents()