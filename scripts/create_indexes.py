#!/usr/bin/env python3
"""
Database indexing script for performance optimization

This script creates indexes on commonly queried fields to improve
database performance for the bookings application.
"""

import os
import sys
from datetime import datetime

# Add the backend directory to Python path so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, mongo


def create_booking_indexes():
    """Create indexes for the bookings collection"""
    print("Creating bookings collection indexes...")

    # Compound index for user queries (most common query pattern)
    mongo.db.bookings.create_index([
        ("user_id", 1),
        ("date_from", 1)
    ], name="bookings_user_date_idx")

    # Agent-based queries
    mongo.db.bookings.create_index([
        ("agent_id", 1),
        ("date_from", 1)
    ], name="bookings_agent_date_idx")

    # Date range queries (for filtering)
    mongo.db.bookings.create_index([
        ("date_from", 1),
        ("date_to", 1)
    ], name="bookings_date_range_idx")

    # Text search index for booking names
    mongo.db.bookings.create_index([
        ("name", "text"),
        ("consultant", "text"),
        ("notes", "text")
    ], name="bookings_text_search_idx")

    # Status and creation time for recent bookings
    mongo.db.bookings.create_index([
        ("created_at", -1)
    ], name="bookings_created_desc_idx")

    # Rate basis filtering
    mongo.db.bookings.create_index([
        ("rate_basis", 1),
        ("date_from", 1)
    ], name="bookings_rate_date_idx")

    print("[SUCCESS] Bookings indexes created successfully")


def create_agent_indexes():
    """Create indexes for the agents collection"""
    print("Creating agents collection indexes...")

    # Email lookup (should be unique)
    mongo.db.agents.create_index([
        ("email", 1)
    ], unique=True, name="agents_email_unique_idx")

    # Location-based queries
    mongo.db.agents.create_index([
        ("location", 1),
        ("created_at", -1)
    ], name="agents_location_created_idx")

    # Text search for agent names and locations
    mongo.db.agents.create_index([
        ("name", "text"),
        ("location", "text")
    ], name="agents_text_search_idx")

    # Commission rate queries (for reporting)
    mongo.db.agents.create_index([
        ("commission_rate", -1)
    ], name="agents_commission_idx")

    print("[SUCCESS] Agents indexes created successfully")


def create_user_indexes():
    """Create indexes for the users collection"""
    print("Creating users collection indexes...")

    # Email lookup (should be unique)
    mongo.db.users.create_index([
        ("email", 1)
    ], unique=True, name="users_email_unique_idx")

    # Role-based queries
    mongo.db.users.create_index([
        ("role", 1),
        ("created_at", -1)
    ], name="users_role_created_idx")

    # Last login tracking
    mongo.db.users.create_index([
        ("last_login", -1)
    ], name="users_last_login_idx")

    # Account status
    mongo.db.users.create_index([
        ("is_active", 1),
        ("created_at", -1)
    ], name="users_active_created_idx")

    print("[SUCCESS] Users indexes created successfully")


def create_document_indexes():
    """Create indexes for the documents collection"""
    print("Creating documents collection indexes...")

    # Booking-document relationship
    mongo.db.documents.create_index([
        ("booking_id", 1),
        ("uploaded_at", -1)
    ], name="documents_booking_uploaded_idx")

    # User's documents
    mongo.db.documents.create_index([
        ("user_id", 1),
        ("uploaded_at", -1)
    ], name="documents_user_uploaded_idx")

    # Category-based queries
    mongo.db.documents.create_index([
        ("category", 1),
        ("booking_id", 1)
    ], name="documents_category_booking_idx")

    # File type and size for analytics
    mongo.db.documents.create_index([
        ("mime_type", 1)
    ], name="documents_mime_type_idx")

    print("[SUCCESS] Documents indexes created successfully")


def create_share_token_indexes():
    """Create indexes for the share_tokens collection"""
    print("Creating share_tokens collection indexes...")

    # Token lookup (primary access pattern)
    mongo.db.share_tokens.create_index([
        ("token", 1)
    ], unique=True, name="share_tokens_token_unique_idx")

    # Booking share tokens
    mongo.db.share_tokens.create_index([
        ("booking_id", 1),
        ("created_at", -1)
    ], name="share_tokens_booking_created_idx")

    # Expiry cleanup
    mongo.db.share_tokens.create_index([
        ("expires_at", 1)
    ], name="share_tokens_expires_idx")

    # User's share tokens
    mongo.db.share_tokens.create_index([
        ("created_by", 1),
        ("created_at", -1)
    ], name="share_tokens_user_created_idx")

    print("[SUCCESS] Share tokens indexes created successfully")


def create_audit_indexes():
    """Create indexes for audit/logging collections (if they exist)"""
    print("Creating audit collection indexes...")

    # Check if audit collections exist
    collections = mongo.db.list_collection_names()

    if 'audit_log' in collections:
        # User activity tracking
        mongo.db.audit_log.create_index([
            ("user_id", 1),
            ("timestamp", -1)
        ], name="audit_user_time_idx")

        # Action-based queries
        mongo.db.audit_log.create_index([
            ("action", 1),
            ("timestamp", -1)
        ], name="audit_action_time_idx")

        # Resource-based queries
        mongo.db.audit_log.create_index([
            ("resource_type", 1),
            ("resource_id", 1),
            ("timestamp", -1)
        ], name="audit_resource_time_idx")

        print("[SUCCESS] Audit log indexes created successfully")

    if 'login_attempts' in collections:
        # Failed login tracking
        mongo.db.login_attempts.create_index([
            ("email", 1),
            ("timestamp", -1)
        ], name="login_attempts_email_time_idx")

        # IP-based tracking
        mongo.db.login_attempts.create_index([
            ("ip_address", 1),
            ("timestamp", -1)
        ], name="login_attempts_ip_time_idx")

        print("[SUCCESS] Login attempts indexes created successfully")


def create_ttl_indexes():
    """Create TTL (Time To Live) indexes for automatic cleanup"""
    print("Creating TTL indexes for automatic cleanup...")

    # Share tokens expire automatically - check if TTL index already exists
    try:
        mongo.db.share_tokens.create_index([
            ("expires_at", 1)
        ], expireAfterSeconds=0, name="share_tokens_ttl_idx")
    except Exception as e:
        if "IndexOptionsConflict" in str(e):
            print("[INFO] TTL index on share_tokens.expires_at already exists with different options")
        else:
            raise e

    # Login attempts cleanup (keep for 30 days)
    collections = mongo.db.list_collection_names()
    if 'login_attempts' in collections:
        mongo.db.login_attempts.create_index([
            ("timestamp", 1)
        ], expireAfterSeconds=2592000, name="login_attempts_ttl_idx")  # 30 days

    # Audit log cleanup (keep for 1 year)
    if 'audit_log' in collections:
        mongo.db.audit_log.create_index([
            ("timestamp", 1)
        ], expireAfterSeconds=31536000, name="audit_log_ttl_idx")  # 1 year

    print("[SUCCESS] TTL indexes created successfully")


def list_existing_indexes():
    """List all existing indexes for review"""
    print("\n[INFO] Current Database Indexes:")
    print("=" * 50)

    collections = ['bookings', 'agents', 'users', 'documents', 'share_tokens']

    for collection_name in collections:
        if collection_name in mongo.db.list_collection_names():
            print(f"\n{collection_name.upper()} Collection:")
            collection = mongo.db[collection_name]
            indexes = collection.list_indexes()

            for idx in indexes:
                name = idx.get('name', 'Unknown')
                keys = list(idx.get('key', {}).keys())
                unique = idx.get('unique', False)
                ttl = idx.get('expireAfterSeconds')

                status = "[INDEX]"
                if unique:
                    status = "[UNIQUE]"
                elif ttl is not None:
                    status = f"[TTL: {ttl}s]"

                print(f"  {status} {name}: {', '.join(keys)}")


def drop_unused_indexes():
    """Drop indexes that might be unused or redundant"""
    print("\n[INFO] Cleaning up unused indexes...")

    # This would need to be customized based on actual usage patterns
    # For now, just report what could be cleaned up
    print("[INFO] Review index usage with db.collection.getIndexes() and db.collection.aggregate([{$indexStats: {}}])")
    print("[INFO] Consider dropping unused indexes to save storage space and write performance")


def main():
    """Main function to create all database indexes"""
    print("[INFO] Starting database index creation...")
    print(f"[INFO] Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Create Flask app context
    app = create_app()
    with app.app_context():
        try:
            # Test database connection
            mongo.db.command('ping')
            print("[SUCCESS] Database connection successful")

            # Create all indexes
            create_booking_indexes()
            create_agent_indexes()
            create_user_indexes()
            create_document_indexes()
            create_share_token_indexes()
            create_audit_indexes()
            create_ttl_indexes()

            print("\n" + "=" * 60)
            print("[SUCCESS] All indexes created successfully!")

            # List current indexes
            list_existing_indexes()

            print(f"\n[INFO] Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("\n[INFO] Performance Tips:")
            print("  • Monitor query performance with explain() commands")
            print("  • Review index usage periodically")
            print("  • Consider compound indexes for common query patterns")
            print("  • Use text indexes for full-text search requirements")

        except Exception as e:
            print(f"[ERROR] Error creating indexes: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    main()