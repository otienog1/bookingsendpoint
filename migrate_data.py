#!/usr/bin/env python3
"""
PostgreSQL to MongoDB Data Migration Script

This script migrates all existing data from PostgreSQL to MongoDB.
It handles users, agents, and bookings with proper relationship mapping.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import DictCursor
from pymongo import MongoClient
from bson import ObjectId

# Load environment variables
load_dotenv()

class DataMigrator:
    def __init__(self):
        # PostgreSQL connection
        self.pg_conn = None
        self.pg_cursor = None
        
        # MongoDB connection
        self.mongo_client = None
        self.mongo_db = None
        
        # ID mapping for relationships
        self.user_id_map = {}  # pg_id -> mongo_id
        self.agent_id_map = {}  # pg_id -> mongo_id
        
        # Statistics
        self.stats = {
            'users': {'migrated': 0, 'errors': 0},
            'agents': {'migrated': 0, 'errors': 0},
            'bookings': {'migrated': 0, 'errors': 0}
        }
        
    def connect_postgresql(self):
        """Connect to PostgreSQL database"""
        try:
            pg_uri = os.getenv('SQLALCHEMY_DATABASE_URI')
            if not pg_uri:
                raise ValueError("SQLALCHEMY_DATABASE_URI not found in environment variables")
            
            print("🔌 Connecting to PostgreSQL...")
            self.pg_conn = psycopg2.connect(pg_uri)
            self.pg_cursor = self.pg_conn.cursor(cursor_factory=DictCursor)
            
            # Test connection
            self.pg_cursor.execute("SELECT version();")
            version = self.pg_cursor.fetchone()
            print(f"✅ Connected to PostgreSQL: {version[0][:50]}...")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to PostgreSQL: {str(e)}")
            return False
    
    def connect_mongodb(self):
        """Connect to MongoDB database"""
        try:
            mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/bookings_db')
            print("🔌 Connecting to MongoDB...")
            
            self.mongo_client = MongoClient(mongo_uri)
            
            # For MongoDB Atlas (mongodb+srv://), use a simple database name
            # For local MongoDB, extract from URI or use default
            if 'mongodb+srv://' in mongo_uri or 'mongodb.net' in mongo_uri:
                # MongoDB Atlas - use simple database name
                db_name = 'bookings_db'
                print("📡 Detected MongoDB Atlas connection")
            elif '/bookings_db' in mongo_uri:
                db_name = 'bookings_db'
            else:
                # Extract database name from local URI
                db_name = 'bookings_db'  # Default fallback
                
            self.mongo_db = self.mongo_client[db_name]
            
            # Test connection
            self.mongo_db.command('ping')
            print(f"✅ Connected to MongoDB database: {db_name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {str(e)}")
            return False
    
    def get_postgresql_tables(self):
        """Check what tables exist in PostgreSQL"""
        try:
            self.pg_cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in self.pg_cursor.fetchall()]
            print(f"📊 Found PostgreSQL tables: {', '.join(tables)}")
            return tables
        except Exception as e:
            print(f"❌ Error fetching table list: {str(e)}")
            return []
    
    def migrate_users(self):
        """Migrate users from PostgreSQL to MongoDB"""
        print("\n👤 Migrating users...")
        
        try:
            # Fetch all users from PostgreSQL
            self.pg_cursor.execute("""
                SELECT id, username, email, password_hash, first_name, last_name, 
                       role, is_active, created_at, updated_at
                FROM users
                ORDER BY id;
            """)
            
            users = self.pg_cursor.fetchall()
            print(f"📥 Found {len(users)} users to migrate")
            
            users_collection = self.mongo_db['users']
            
            for user in users:
                try:
                    # Convert PostgreSQL row to MongoDB document
                    mongo_user = {
                        'username': user['username'],
                        'email': user['email'],
                        'password_hash': user['password_hash'],
                        'first_name': user['first_name'],
                        'last_name': user['last_name'],
                        'role': user['role'] or 'user',
                        'is_active': user['is_active'] if user['is_active'] is not None else True,
                        'created_at': user['created_at'] or datetime.utcnow(),
                        'updated_at': user['updated_at'] or datetime.utcnow()
                    }
                    
                    # Insert into MongoDB
                    result = users_collection.insert_one(mongo_user)
                    
                    # Map PostgreSQL ID to MongoDB ObjectId for relationships
                    self.user_id_map[user['id']] = result.inserted_id
                    
                    self.stats['users']['migrated'] += 1
                    print(f"  ✅ Migrated user: {user['username']} ({user['id']} -> {result.inserted_id})")
                    
                except Exception as e:
                    self.stats['users']['errors'] += 1
                    print(f"  ❌ Error migrating user {user['username']}: {str(e)}")
                    
        except Exception as e:
            print(f"❌ Error in users migration: {str(e)}")
    
    def migrate_agents(self):
        """Migrate agents from PostgreSQL to MongoDB"""
        print("\n🏢 Migrating agents...")
        
        try:
            # Fetch all agents from PostgreSQL
            self.pg_cursor.execute("""
                SELECT id, name, company, email, phone, country, address, notes, 
                       is_active, user_id, created_at, updated_at
                FROM agents
                ORDER BY id;
            """)
            
            agents = self.pg_cursor.fetchall()
            print(f"📥 Found {len(agents)} agents to migrate")
            
            agents_collection = self.mongo_db['agents']
            
            for agent in agents:
                try:
                    # Map PostgreSQL user_id to MongoDB ObjectId
                    mongo_user_id = self.user_id_map.get(agent['user_id'])
                    if not mongo_user_id and agent['user_id']:
                        print(f"  ⚠️  Warning: User ID {agent['user_id']} not found for agent {agent['name']}")
                        continue
                    
                    # Convert PostgreSQL row to MongoDB document
                    mongo_agent = {
                        'name': agent['name'],
                        'company': agent['company'],
                        'email': agent['email'],
                        'phone': agent['phone'],
                        'country': agent['country'],
                        'address': agent['address'],
                        'notes': agent['notes'],
                        'is_active': agent['is_active'] if agent['is_active'] is not None else True,
                        'user_id': mongo_user_id,
                        'created_at': agent['created_at'] or datetime.utcnow(),
                        'updated_at': agent['updated_at'] or datetime.utcnow()
                    }
                    
                    # Insert into MongoDB
                    result = agents_collection.insert_one(mongo_agent)
                    
                    # Map PostgreSQL ID to MongoDB ObjectId for relationships
                    self.agent_id_map[agent['id']] = result.inserted_id
                    
                    self.stats['agents']['migrated'] += 1
                    print(f"  ✅ Migrated agent: {agent['name']} ({agent['id']} -> {result.inserted_id})")
                    
                except Exception as e:
                    self.stats['agents']['errors'] += 1
                    print(f"  ❌ Error migrating agent {agent['name']}: {str(e)}")
                    
        except Exception as e:
            print(f"❌ Error in agents migration: {str(e)}")
    
    def migrate_bookings(self):
        """Migrate bookings from PostgreSQL to MongoDB"""
        print("\n📅 Migrating bookings...")
        
        try:
            # Fetch all bookings from PostgreSQL
            self.pg_cursor.execute("""
                SELECT id, name, date_from, date_to, country, pax, ladies, men, 
                       children, teens, agent_id, agent, consultant, user_id, 
                       created_at, updated_at
                FROM bookings
                ORDER BY id;
            """)
            
            bookings = self.pg_cursor.fetchall()
            print(f"📥 Found {len(bookings)} bookings to migrate")
            
            bookings_collection = self.mongo_db['bookings']
            
            for booking in bookings:
                try:
                    # Map PostgreSQL user_id to MongoDB ObjectId
                    mongo_user_id = self.user_id_map.get(booking['user_id'])
                    if not mongo_user_id and booking['user_id']:
                        print(f"  ⚠️  Warning: User ID {booking['user_id']} not found for booking {booking['name']}")
                        continue
                    
                    # Map PostgreSQL agent_id to MongoDB ObjectId
                    mongo_agent_id = self.agent_id_map.get(booking['agent_id'])
                    if not mongo_agent_id and booking['agent_id']:
                        print(f"  ⚠️  Warning: Agent ID {booking['agent_id']} not found for booking {booking['name']}")
                        # Skip this booking if agent is required
                        continue
                    
                    # Convert PostgreSQL row to MongoDB document
                    mongo_booking = {
                        'name': booking['name'],
                        'date_from': booking['date_from'],
                        'date_to': booking['date_to'],
                        'country': booking['country'],
                        'pax': booking['pax'] or 0,
                        'ladies': booking['ladies'] or 0,
                        'men': booking['men'] or 0,
                        'children': booking['children'] or 0,
                        'teens': booking['teens'] or 0,
                        'agent_id': mongo_agent_id,
                        'consultant': booking['consultant'],
                        'user_id': mongo_user_id,
                        'created_at': booking['created_at'] or datetime.utcnow(),
                        'updated_at': booking['updated_at'] or datetime.utcnow()
                    }
                    
                    # Insert into MongoDB
                    result = bookings_collection.insert_one(mongo_booking)
                    
                    self.stats['bookings']['migrated'] += 1
                    print(f"  ✅ Migrated booking: {booking['name']} ({booking['id']} -> {result.inserted_id})")
                    
                except Exception as e:
                    self.stats['bookings']['errors'] += 1
                    print(f"  ❌ Error migrating booking {booking['name']}: {str(e)}")
                    
        except Exception as e:
            print(f"❌ Error in bookings migration: {str(e)}")
    
    def verify_migration(self):
        """Verify the migration by counting documents"""
        print("\n🔍 Verifying migration...")
        
        try:
            # Count documents in MongoDB
            users_count = self.mongo_db['users'].count_documents({})
            agents_count = self.mongo_db['agents'].count_documents({})
            bookings_count = self.mongo_db['bookings'].count_documents({})
            
            print(f"📊 MongoDB document counts:")
            print(f"  Users: {users_count}")
            print(f"  Agents: {agents_count}")
            print(f"  Bookings: {bookings_count}")
            
            # Check for any orphaned relationships
            print("\n🔗 Checking relationships...")
            
            # Check agents without valid users
            agents_without_users = self.mongo_db['agents'].count_documents({
                "user_id": {"$exists": False}
            })
            if agents_without_users > 0:
                print(f"  ⚠️  Found {agents_without_users} agents without user references")
            
            # Check bookings without valid users
            bookings_without_users = self.mongo_db['bookings'].count_documents({
                "user_id": {"$exists": False}
            })
            if bookings_without_users > 0:
                print(f"  ⚠️  Found {bookings_without_users} bookings without user references")
            
            # Check bookings without valid agents
            bookings_without_agents = self.mongo_db['bookings'].count_documents({
                "agent_id": {"$exists": False}
            })
            if bookings_without_agents > 0:
                print(f"  ⚠️  Found {bookings_without_agents} bookings without agent references")
            
            print("✅ Verification completed")
            
        except Exception as e:
            print(f"❌ Error during verification: {str(e)}")
    
    def cleanup_mongodb(self):
        """Clean up MongoDB collections before migration (optional)"""
        response = input("\n❓ Do you want to clear existing MongoDB data before migration? (y/N): ")
        if response.lower() == 'y':
            print("🗑️  Clearing MongoDB collections...")
            self.mongo_db['users'].delete_many({})
            self.mongo_db['agents'].delete_many({})
            self.mongo_db['bookings'].delete_many({})
            print("✅ MongoDB collections cleared")
    
    def print_summary(self):
        """Print migration summary"""
        print("\n" + "="*50)
        print("🎉 MIGRATION SUMMARY")
        print("="*50)
        
        total_migrated = sum(stat['migrated'] for stat in self.stats.values())
        total_errors = sum(stat['errors'] for stat in self.stats.values())
        
        for collection, stat in self.stats.items():
            print(f"{collection.capitalize():>10}: {stat['migrated']:>3} migrated, {stat['errors']:>3} errors")
        
        print("-" * 50)
        print(f"{'TOTAL':>10}: {total_migrated:>3} migrated, {total_errors:>3} errors")
        print("="*50)
        
        if total_errors == 0:
            print("🎊 Migration completed successfully with no errors!")
        else:
            print(f"⚠️  Migration completed with {total_errors} errors. Check the logs above.")
        
        print("\n📝 Next steps:")
        print("1. Update your .env file to use MongoDB:")
        print("   MONGO_URI=mongodb://localhost:27017/bookings_db")
        print("2. Test your application with the migrated data")
        print("3. Run test_migration.py to verify functionality")
    
    def close_connections(self):
        """Close database connections"""
        if self.pg_cursor:
            self.pg_cursor.close()
        if self.pg_conn:
            self.pg_conn.close()
        if self.mongo_client:
            self.mongo_client.close()
    
    def migrate(self):
        """Run the complete migration process"""
        print("🚀 Starting PostgreSQL to MongoDB Migration")
        print("=" * 50)
        
        try:
            # Connect to databases
            if not self.connect_postgresql():
                return False
            
            if not self.connect_mongodb():
                return False
            
            # Check PostgreSQL tables
            tables = self.get_postgresql_tables()
            required_tables = ['users', 'agents', 'bookings']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                print(f"❌ Missing required tables in PostgreSQL: {', '.join(missing_tables)}")
                return False
            
            # Optional cleanup
            self.cleanup_mongodb()
            
            # Run migrations in order (users first, then agents, then bookings)
            self.migrate_users()
            self.migrate_agents() 
            self.migrate_bookings()
            
            # Verify migration
            self.verify_migration()
            
            # Print summary
            self.print_summary()
            
            return True
            
        except Exception as e:
            print(f"💥 Critical error during migration: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            self.close_connections()


def main():
    """Main function"""
    print("🧪 PostgreSQL to MongoDB Data Migration Tool")
    print("This tool will migrate your existing PostgreSQL data to MongoDB")
    print()
    
    # Create migrator and run migration
    migrator = DataMigrator()
    success = migrator.migrate()
    
    if success:
        print("\n✨ Migration completed! You can now switch to MongoDB.")
    else:
        print("\n💔 Migration failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()