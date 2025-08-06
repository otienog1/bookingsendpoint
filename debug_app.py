#!/usr/bin/env python3
"""
Debug Script for MongoDB Application
This script helps identify where errors are occurring in the application.
"""

import os
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_imports():
    """Test all imports to identify issues"""
    print("🧪 Testing imports...")
    
    try:
        print("  📦 Importing Flask...")
        from flask import Flask
        print("  ✅ Flask imported successfully")
        
        print("  📦 Importing PyMongo...")
        from pymongo import MongoClient
        from flask_pymongo import PyMongo
        print("  ✅ PyMongo imported successfully")
        
        print("  📦 Importing app components...")
        from app import mongo
        print("  ✅ App mongo imported successfully")
        
        print("  📦 Importing MongoDB models...")
        from app.mongodb_models import User, Agent, Booking
        print("  ✅ MongoDB models imported successfully")
        
        print("  📦 Importing app...")
        from app import app
        print("  ✅ App imported successfully")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import error: {str(e)}")
        traceback.print_exc()
        return False

def test_app_context():
    """Test application context and MongoDB connection"""
    print("\n🔧 Testing application context...")
    
    try:
        from app import app, mongo
        
        with app.app_context():
            print("  ✅ Application context created")
            
            # Test MongoDB connection
            print("  🔌 Testing MongoDB connection...")
            result = mongo.db.command('ping')
            print(f"  ✅ MongoDB ping successful: {result}")
            
            # Test database access
            print("  🗄️  Testing database access...")
            db_name = mongo.db.name
            print(f"  ✅ Connected to database: {db_name}")
            
            # List collections
            collections = mongo.db.list_collection_names()
            print(f"  📂 Collections: {collections if collections else 'None'}")
            
            return True
            
    except Exception as e:
        print(f"  ❌ App context error: {str(e)}")
        traceback.print_exc()
        return False

def test_user_model():
    """Test User model operations"""
    print("\n👤 Testing User model...")
    
    try:
        from app import app
        from app.mongodb_models import User
        
        with app.app_context():
            print("  📋 Testing User.find_one...")
            admin = User.find_one({"role": "admin"})
            print(f"  ✅ Find admin result: {admin is not None}")
            
            if admin:
                print("  📋 Testing User.to_dict...")
                user_dict = User.to_dict(admin)
                print(f"  ✅ User dict created: {user_dict is not None}")
                
                if user_dict:
                    print(f"  📝 Admin username: {user_dict.get('username', 'N/A')}")
                    print(f"  📝 Admin role: {user_dict.get('role', 'N/A')}")
            
            return True
            
    except Exception as e:
        print(f"  ❌ User model error: {str(e)}")
        traceback.print_exc()
        return False

def test_auth_decorator():
    """Test authentication decorator components"""
    print("\n🔐 Testing authentication components...")
    
    try:
        from app.authbp import token_required
        print("  ✅ token_required imported successfully")
        
        import jwt
        print("  ✅ JWT imported successfully")
        
        # Test JWT decoding (with dummy data)
        from app import app
        with app.app_context():
            secret = app.config.get('SECRET_KEY')
            algorithm = app.config.get('JWT_ALGORITHM', 'HS256')
            print(f"  🔑 JWT Secret configured: {secret is not None}")
            print(f"  🔧 JWT Algorithm: {algorithm}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Auth test error: {str(e)}")
        traceback.print_exc()
        return False

def run_basic_app_test():
    """Run a basic Flask app test"""
    print("\n🌐 Testing basic Flask app startup...")
    
    try:
        from app import app
        
        # Test app configuration
        print(f"  🔧 Debug mode: {app.config.get('DEBUG', 'Not set')}")
        print(f"  🔧 Secret key configured: {app.config.get('SECRET_KEY') is not None}")
        print(f"  🔧 MongoDB URI configured: {app.config.get('MONGO_URI') is not None}")
        
        # Test a simple route (if any exist)
        with app.test_client() as client:
            print("  🧪 Testing app with test client...")
            # Try to access a health endpoint or similar
            try:
                response = client.get('/auth/health')
                print(f"  📊 Health endpoint status: {response.status_code}")
            except:
                print("  ℹ️  Health endpoint not accessible (expected)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Flask app test error: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Main debugging function"""
    print("🔍 MongoDB Application Debug Tool")
    print("=" * 50)
    
    # Test each component
    tests = [
        ("Imports", test_imports),
        ("App Context", test_app_context),
        ("User Model", test_user_model),
        ("Auth Components", test_auth_decorator),
        ("Basic App", run_basic_app_test)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"💥 Critical error in {test_name}: {str(e)}")
            results[test_name] = False
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 DEBUGGING SUMMARY")
    print("=" * 50)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:>15}: {status}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    print(f"\n📈 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application should work correctly.")
        print("\n🚀 Try running: python run.py")
    else:
        print("⚠️  Some tests failed. Check the errors above for details.")
        print("\n🔧 Common fixes:")
        print("- Ensure MongoDB is running and accessible")
        print("- Check your MONGO_URI in .env file")
        print("- Verify all required packages are installed")

if __name__ == "__main__":
    main()