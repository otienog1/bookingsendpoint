#!/usr/bin/env python3
"""
Simple test to isolate the NoneType error
"""

try:
    print("🧪 Testing basic imports...")
    from app import app, mongo
    print("✅ App and mongo imported")

    print("🧪 Testing app context...")
    with app.app_context():
        print("✅ App context created")
        
        print("🧪 Testing MongoDB connection...")
        result = mongo.db.command('ping')
        print(f"✅ MongoDB ping: {result}")
        
        print("🧪 Testing User model import...")
        from app.mongodb_models import User
        print("✅ User model imported")
        
        print("🧪 Testing User operations...")
        # Test find_one with empty query
        admin = User.find_one({"role": "admin"})
        print(f"✅ Find admin result: {admin is not None}")
        
        if admin is None:
            print("ℹ️  No admin found - this is expected on first run")
            
            print("🧪 Testing User creation...")
            new_admin = User.create_user(
                username='test_admin',
                email='test@example.com', 
                password='test123',
                role='admin'
            )
            print(f"✅ Created admin: {new_admin is not None}")
            
            if new_admin:
                print("🧪 Testing User.to_dict...")
                admin_dict = User.to_dict(new_admin)
                print(f"✅ User dict: {admin_dict}")
                
                # Clean up
                User.delete_one({"_id": new_admin["_id"]})
                print("🧹 Test user cleaned up")
        else:
            print("🧪 Testing User.to_dict on existing admin...")
            admin_dict = User.to_dict(admin)
            print(f"✅ Admin dict: {admin_dict}")

    print("\n🎉 All tests passed!")

except Exception as e:
    print(f"\n💥 Error: {str(e)}")
    import traceback
    traceback.print_exc()