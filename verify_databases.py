#!/usr/bin/env python3
"""
Database Verification Script
This script checks both PostgreSQL and MongoDB databases to compare data.
"""

import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import DictCursor
from pymongo import MongoClient

# Load environment variables
load_dotenv()

def check_postgresql():
    """Check PostgreSQL database contents"""
    print("🐘 Checking PostgreSQL Database...")
    
    try:
        pg_uri = os.getenv('SQLALCHEMY_DATABASE_URI')
        if not pg_uri:
            print("❌ SQLALCHEMY_DATABASE_URI not found")
            return None
        
        # Connect to PostgreSQL
        conn = psycopg2.connect(pg_uri)
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        # Get table counts
        counts = {}
        tables = ['users', 'agents', 'bookings']
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                counts[table] = count
                print(f"  📊 {table}: {count} records")
            except Exception as e:
                print(f"  ❌ Error counting {table}: {str(e)}")
                counts[table] = 0
        
        # Get sample data
        print("\n  📋 Sample data:")
        for table in tables:
            try:
                cursor.execute(f"SELECT * FROM {table} LIMIT 3;")
                rows = cursor.fetchall()
                if rows:
                    columns = [desc[0] for desc in cursor.description]
                    print(f"    {table} columns: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}")
                else:
                    print(f"    {table}: No data")
            except Exception as e:
                print(f"    ❌ Error sampling {table}: {str(e)}")
        
        cursor.close()
        conn.close()
        print("✅ PostgreSQL check completed")
        return counts
        
    except Exception as e:
        print(f"❌ Error checking PostgreSQL: {str(e)}")
        return None

def check_mongodb():
    """Check MongoDB database contents"""
    print("\n🍃 Checking MongoDB Database...")
    
    try:
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/bookings_db')
        
        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        
        # For MongoDB Atlas (mongodb+srv://), use a simple database name
        # For local MongoDB, extract from URI or use default
        if 'mongodb+srv://' in mongo_uri or 'mongodb.net' in mongo_uri:
            # MongoDB Atlas - use simple database name
            db_name = 'bookings_db'
            print("  📡 Detected MongoDB Atlas connection")
        elif '/bookings_db' in mongo_uri:
            db_name = 'bookings_db'
        else:
            # Extract database name from local URI or use default
            db_name = 'bookings_db'
            
        db = client[db_name]
        
        # Test connection
        db.command('ping')
        print(f"  🔌 Connected to database: {db_name}")
        
        # Get collection counts
        counts = {}
        collections = ['users', 'agents', 'bookings']
        
        for collection in collections:
            try:
                count = db[collection].count_documents({})
                counts[collection] = count
                print(f"  📊 {collection}: {count} documents")
            except Exception as e:
                print(f"  ❌ Error counting {collection}: {str(e)}")
                counts[collection] = 0
        
        # Get sample data
        print("\n  📋 Sample data:")
        for collection in collections:
            try:
                sample = db[collection].find_one()
                if sample:
                    fields = list(sample.keys())[:5]
                    print(f"    {collection} fields: {', '.join(fields)}{'...' if len(sample.keys()) > 5 else ''}")
                else:
                    print(f"    {collection}: No data")
            except Exception as e:
                print(f"    ❌ Error sampling {collection}: {str(e)}")
        
        # Check indexes
        print("\n  🗂️  Indexes:")
        for collection in collections:
            try:
                indexes = list(db[collection].list_indexes())
                index_names = [idx['name'] for idx in indexes if idx['name'] != '_id_']
                if index_names:
                    print(f"    {collection}: {', '.join(index_names)}")
                else:
                    print(f"    {collection}: Only default _id index")
            except Exception as e:
                print(f"    ❌ Error checking indexes for {collection}: {str(e)}")
        
        client.close()
        print("✅ MongoDB check completed")
        return counts
        
    except Exception as e:
        print(f"❌ Error checking MongoDB: {str(e)}")
        return None

def compare_counts(pg_counts, mongo_counts):
    """Compare record counts between databases"""
    if not pg_counts or not mongo_counts:
        print("\n⚠️  Cannot compare - one or both databases unavailable")
        return
    
    print("\n🔄 Comparing Database Contents:")
    print("-" * 40)
    print(f"{'Collection':<10} {'PostgreSQL':<12} {'MongoDB':<10} {'Status'}")
    print("-" * 40)
    
    all_match = True
    
    for collection in ['users', 'agents', 'bookings']:
        pg_count = pg_counts.get(collection, 0)
        mongo_count = mongo_counts.get(collection, 0)
        
        if pg_count == mongo_count:
            status = "✅ Match"
        else:
            status = "❌ Differ"
            all_match = False
        
        print(f"{collection:<10} {pg_count:<12} {mongo_count:<10} {status}")
    
    print("-" * 40)
    
    if all_match:
        print("🎉 All collections have matching counts!")
    else:
        print("⚠️  Some collections have different counts.")
        print("   This might be expected if migration is in progress.")

def main():
    """Main function"""
    print("🔍 Database Verification Tool")
    print("This tool checks both PostgreSQL and MongoDB databases")
    print("=" * 50)
    
    # Check PostgreSQL
    pg_counts = check_postgresql()
    
    # Check MongoDB  
    mongo_counts = check_mongodb()
    
    # Compare results
    compare_counts(pg_counts, mongo_counts)
    
    print("\n" + "=" * 50)
    if pg_counts and sum(pg_counts.values()) > 0:
        print("✅ PostgreSQL has data - ready for migration")
    else:
        print("ℹ️  PostgreSQL appears empty or unavailable")
    
    if mongo_counts and sum(mongo_counts.values()) > 0:
        print("✅ MongoDB has data - migration may be complete")
    else:
        print("ℹ️  MongoDB appears empty - ready to receive migrated data")
    
    print("\n💡 Use this tool before and after running migrate_data.py")
    print("   to verify your data migration was successful!")

if __name__ == "__main__":
    main()