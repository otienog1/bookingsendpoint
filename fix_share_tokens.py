#!/usr/bin/env python3
"""
Fix existing share tokens to include all categories
"""
import os
import sys
from bson import ObjectId
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, mongo

def fix_share_tokens():
    """Update existing share tokens to include all categories."""
    app = create_app()

    with app.app_context():
        try:
            print("=== Fixing Share Tokens to Include All Categories ===\n")

            # Get all active share tokens
            current_time = datetime.utcnow()
            active_tokens = list(mongo.db.share_tokens.find({
                "expires_at": {"$gt": current_time}
            }))

            print(f"Found {len(active_tokens)} active share tokens")

            all_categories = ['Voucher', 'Air Ticket', 'Invoice', 'Other']

            for i, token in enumerate(active_tokens, 1):
                print(f"\nToken {i}:")
                print(f"  Token: {token['token']}")
                print(f"  Current categories: {token.get('categories', [])}")

                # Update to include all categories
                result = mongo.db.share_tokens.update_one(
                    {"_id": token["_id"]},
                    {"$set": {"categories": all_categories}}
                )

                if result.modified_count > 0:
                    print(f"  [OK] Updated to include all categories: {all_categories}")
                else:
                    print(f"  [SKIP] No update needed")

            print(f"\n=== Verification ===")

            # Test the specific tokens mentioned
            test_tokens = [
                "FVPdX5_lM7iKQc3vGVIHSg",
                "iiCOEMJgbjAnVPKLvqfCnQ"
            ]

            for token in test_tokens:
                share_record = mongo.db.share_tokens.find_one({"token": token})
                if share_record:
                    print(f"\nToken {token}:")
                    print(f"  Categories: {share_record.get('categories', [])}")
                    print(f"  Expires: {share_record.get('expires_at')}")

                    # Test document query
                    booking_id = share_record['booking_id']
                    documents = list(mongo.db.booking_documents.find({
                        "booking_id": booking_id,
                        "category": {"$in": share_record.get('categories', [])}
                    }))
                    print(f"  Will show {len(documents)} documents")
                    for doc in documents:
                        print(f"    - {doc.get('filename', 'No filename')} ({doc.get('category', 'No category')})")
                else:
                    print(f"\nToken {token}: Not found")

        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    fix_share_tokens()