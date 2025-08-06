#!/usr/bin/env python3
"""
MongoDB Atlas Connection Test
This script specifically tests your MongoDB Atlas connection and database setup.
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

# Load environment variables
load_dotenv()

def test_atlas_connection():
    """Test MongoDB Atlas connection and basic operations"""
    print("🌍 Testing MongoDB Atlas Connection")
    print("=" * 50)
    
    try:
        # Get MongoDB URI from environment
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            print("❌ MONGO_URI not found in .env file")
            return False
        
        print(f"🔗 Connection URI: {mongo_uri[:50]}...")
        
        # Connect to MongoDB Atlas
        print("🔌 Connecting to MongoDB Atlas...")
        client = MongoClient(mongo_uri)
        
        # Use simple database name for Atlas
        db_name = 'bookings_db'
        db = client[db_name]
        
        # Test connection with ping
        print("🏓 Testing connection with ping...")
        result = db.command('ping')
        print(f"✅ Ping successful: {result}")
        
        # Test database operations
        print(f"\n📊 Testing database operations on '{db_name}'...")
        
        # List existing collections
        collections = db.list_collection_names()
        print(f"📂 Existing collections: {collections if collections else 'None'}")
        
        # Test creating a test collection and document
        test_collection = db['test_connection']
        
        # Insert a test document
        test_doc = {
            'test': True,
            'message': 'MongoDB Atlas connection test',
            'timestamp': '2024-01-01T00:00:00Z'
        }
        
        print("📝 Inserting test document...")
        result = test_collection.insert_one(test_doc)
        print(f"✅ Document inserted with ID: {result.inserted_id}")
        
        # Find the test document
        print("🔍 Finding test document...")
        found_doc = test_collection.find_one({'_id': result.inserted_id})
        print(f"✅ Document found: {found_doc['message']}")
        
        # Update the test document
        print("✏️  Updating test document...")
        test_collection.update_one(
            {'_id': result.inserted_id},
            {'$set': {'updated': True}}
        )
        
        # Verify update
        updated_doc = test_collection.find_one({'_id': result.inserted_id})
        print(f"✅ Document updated: {updated_doc.get('updated', False)}")
        
        # Clean up test document
        print("🧹 Cleaning up test document...")
        test_collection.delete_one({'_id': result.inserted_id})
        print("✅ Test document deleted")
        
        # Clean up test collection if it was created
        if 'test_connection' not in collections:
            db.drop_collection('test_connection')
            print("✅ Test collection removed")
        
        # Show database stats
        print(f"\n📈 Database statistics:")
        stats = db.command('dbStats')
        print(f"  Database: {stats['db']}")
        print(f"  Collections: {stats['collections']}")
        print(f"  Data Size: {stats['dataSize']} bytes")
        print(f"  Storage Size: {stats['storageSize']} bytes")
        
        client.close()
        
        print("\n🎉 MongoDB Atlas connection test completed successfully!")
        print("✅ Your database is ready for migration!")
        return True
        
    except Exception as e:
        print(f"\n❌ MongoDB Atlas connection test failed: {str(e)}")
        
        # Provide helpful troubleshooting tips
        print("\n🔧 Troubleshooting tips:")
        print("1. Check your MONGO_URI in the .env file")
        print("2. Ensure your IP address is whitelisted in MongoDB Atlas")
        print("3. Verify your username and password are correct")
        print("4. Check if your cluster is running and accessible")
        print("5. Make sure you have sufficient permissions on the database")
        
        return False

def show_connection_info():
    """Show information about the MongoDB connection"""
    mongo_uri = os.getenv('MONGO_URI', 'Not configured')
    
    print("\n📋 Current MongoDB Configuration:")
    print("-" * 40)
    
    if 'mongodb+srv://' in mongo_uri:
        print("🌍 Type: MongoDB Atlas (Cloud)")
        print("🔗 Protocol: SRV (mongodb+srv://)")
        
        # Extract cluster info
        if '@' in mongo_uri:
            cluster_part = mongo_uri.split('@')[1].split('/')[0]
            print(f"🏠 Cluster: {cluster_part}")
    elif 'mongodb://' in mongo_uri:
        print("💻 Type: Local MongoDB")
        print("🔗 Protocol: Standard (mongodb://)")
    else:
        print("❓ Type: Unknown or not configured")
    
    print(f"🔑 URI: {mongo_uri[:50]}..." if len(mongo_uri) > 50 else f"🔑 URI: {mongo_uri}")
    print("🗄️ Database: bookings_db (will be used)")

def main():
    """Main function"""
    print("🧪 MongoDB Atlas Connection Test Tool")
    
    # Show current configuration
    show_connection_info()
    
    # Test the connection
    success = test_atlas_connection()
    
    if success:
        print("\n🚀 You can now run the data migration:")
        print("   python migrate_data.py")
    else:
        print("\n🛠️ Please fix the connection issues before proceeding.")

if __name__ == "__main__":
    main()