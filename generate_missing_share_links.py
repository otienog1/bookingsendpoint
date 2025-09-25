#!/usr/bin/env python3
"""
Script to generate share links for all bookings that don't have one.
This will create share tokens for existing bookings that were created before
the share functionality was implemented.
"""

import os
import sys
import time
import secrets
from datetime import datetime, timezone
from bson import ObjectId

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Import Flask app and database models
from app import create_app
from app import mongo
from app.mongodb_models import Booking

def generate_share_token_for_existing_booking(booking_id, user_id, categories=['Voucher', 'Air Ticket'], expires_in_seconds=604800):
    """Generate a share token for an existing booking."""
    try:
        # Generate a short random token ID
        token_id = secrets.token_urlsafe(16)
        expires_at_timestamp = int(time.time()) + expires_in_seconds
        expires_at_datetime = datetime.fromtimestamp(expires_at_timestamp)

        # Create share URL
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
        share_url = f"{frontend_url}/share/{token_id}"

        # Store share token in database
        share_record = {
            "booking_id": ObjectId(booking_id),
            "token": token_id,
            "categories": categories,
            "expires_at": expires_at_datetime,
            "created_at": datetime.now(timezone.utc),
            "created_by": ObjectId(user_id),
            "used_count": 0
        }

        result = mongo.db.share_tokens.insert_one(share_record)

        if result.inserted_id:
            return {
                "token": token_id,
                "share_url": share_url,
                "expires_at": expires_at_datetime.isoformat(),
                "categories": categories
            }
        else:
            return None

    except Exception as e:
        print(f"Error generating share token for booking {booking_id}: {str(e)}")
        return None

def get_bookings_without_share_links():
    """Find all bookings that don't have active share links."""
    try:
        # Get all booking IDs that have share tokens
        bookings_with_shares = mongo.db.share_tokens.distinct("booking_id")

        # Get all bookings that don't have share tokens
        bookings_without_shares = mongo.db.bookings.find({
            "_id": {"$nin": bookings_with_shares}
        })

        return list(bookings_without_shares)
    except Exception as e:
        print(f"Error querying bookings: {str(e)}")
        return []

def main():
    """Main function to generate share links for all bookings without them."""
    print("Starting share link generation for bookings without them...")

    # Create Flask app context
    app = create_app()
    with app.app_context():
        try:
            # Get bookings without share links
            bookings_without_shares = get_bookings_without_share_links()

            if not bookings_without_shares:
                print("SUCCESS: All bookings already have share links!")
                return

            print(f"Found {len(bookings_without_shares)} bookings without share links.")
            print("Generating share links...")

            success_count = 0
            error_count = 0

            for booking in bookings_without_shares:
                booking_id = str(booking['_id'])
                user_id = str(booking['user_id'])
                booking_name = booking.get('name', 'Unknown')

                print(f"Processing booking: {booking_name} (ID: {booking_id})")

                # Generate share link
                result = generate_share_token_for_existing_booking(
                    booking_id=booking_id,
                    user_id=user_id,
                    categories=['Voucher', 'Air Ticket'],  # Default categories
                    expires_in_seconds=604800 * 4  # 4 weeks for existing bookings
                )

                if result:
                    print(f"  [OK] Generated share link: {result['share_url']}")
                    success_count += 1
                else:
                    print(f"  [ERROR] Failed to generate share link")
                    error_count += 1

            print(f"\n=== Summary ===")
            print(f"  Successfully generated: {success_count} share links")
            print(f"  Errors: {error_count}")
            print(f"  Total processed: {len(bookings_without_shares)}")

            if success_count > 0:
                print(f"\nSUCCESS: Generated {success_count} share links!")

            if error_count > 0:
                print(f"\nWARNING: {error_count} bookings had errors - check the logs above.")

        except Exception as e:
            print(f"ERROR: Error in main process: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    main()