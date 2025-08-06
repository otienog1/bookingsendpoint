#!/usr/bin/env python3
"""
Environment Configuration Update Script
This script helps update your .env file to use MongoDB after migration.
"""

import os
import shutil
from datetime import datetime

def backup_env_file():
    """Create a backup of the current .env file"""
    if os.path.exists('.env'):
        backup_name = f'.env.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy('.env', backup_name)
        print(f"📋 Created backup: {backup_name}")
        return backup_name
    return None

def update_env_for_mongodb():
    """Update .env file to use MongoDB configuration"""
    
    print("🔧 Updating .env file for MongoDB...")
    
    # Create backup first
    backup_file = backup_env_file()
    
    # Read current .env file
    env_lines = []
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            env_lines = f.readlines()
    
    # Process lines
    updated_lines = []
    found_mongo_uri = False
    found_postgres_uri = False
    
    for line in env_lines:
        line = line.strip()
        
        # Comment out PostgreSQL URI
        if line.startswith('SQLALCHEMY_DATABASE_URI='):
            updated_lines.append(f"# Migrated to MongoDB - {line}\n")
            found_postgres_uri = True
        # Check if MongoDB URI already exists
        elif line.startswith('MONGO_URI='):
            updated_lines.append(line + '\n')
            found_mongo_uri = True
        else:
            updated_lines.append(line + '\n')
    
    # Add MongoDB URI if not found
    if not found_mongo_uri:
        updated_lines.append('\n# MongoDB Configuration\n')
        updated_lines.append('MONGO_URI=mongodb://localhost:27017/bookings_db\n')
        print("➕ Added MONGO_URI configuration")
    
    if found_postgres_uri:
        print("💭 Commented out SQLALCHEMY_DATABASE_URI")
    
    # Write updated .env file
    with open('.env', 'w') as f:
        f.writelines(updated_lines)
    
    print("✅ .env file updated for MongoDB")
    
    # Show MongoDB configuration options
    print("\n📝 MongoDB Configuration Options:")
    print("For local MongoDB:")
    print("  MONGO_URI=mongodb://localhost:27017/bookings_db")
    print("\nFor MongoDB with authentication:")
    print("  MONGO_URI=mongodb://username:password@host:port/database")
    print("\nFor MongoDB Atlas (cloud):")
    print("  MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/database")

def show_migration_instructions():
    """Show step-by-step migration instructions"""
    print("\n" + "="*60)
    print("📋 DATA MIGRATION INSTRUCTIONS")
    print("="*60)
    
    print("\n1️⃣  Install Dependencies:")
    print("   pipenv install")
    
    print("\n2️⃣  Start MongoDB:")
    print("   On Windows: mongod")
    print("   On macOS:   brew services start mongodb/brew/mongodb-community")
    print("   On Linux:   sudo systemctl start mongod")
    
    print("\n3️⃣  Run Data Migration:")
    print("   python migrate_data.py")
    print("   ⚠️  This will read from PostgreSQL and write to MongoDB")
    
    print("\n4️⃣  Verify Migration:")
    print("   python test_migration.py")
    
    print("\n5️⃣  Update Application:")
    print("   The app will now use MongoDB instead of PostgreSQL")
    print("   python run.py")
    
    print("\n6️⃣  Test Your Application:")
    print("   - Test login/registration")
    print("   - Test creating/editing bookings") 
    print("   - Test agent management")
    print("   - Test CSV imports")
    
    print("\n" + "="*60)
    print("⚠️  IMPORTANT NOTES:")
    print("- Keep your PostgreSQL data until you verify everything works")
    print("- The migration script will ask before clearing MongoDB data")
    print("- Check the migration logs for any errors or warnings")
    print("- Test all functionality before decommissioning PostgreSQL")
    print("="*60)

def main():
    """Main function"""
    print("🛠️  Environment Configuration Update Tool")
    print("This tool will update your .env file for MongoDB migration")
    print()
    
    # Update environment file
    update_env_for_mongodb()
    
    # Show migration instructions
    show_migration_instructions()
    
    print("\n✨ Environment configuration updated!")
    print("You can now run the data migration script.")

if __name__ == "__main__":
    main()