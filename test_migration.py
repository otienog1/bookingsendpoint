#!/usr/bin/env python3
"""
Test script to validate MongoDB migration
"""

from app import create_app
from app.mongodb_models import User, Agent, Booking
from datetime import datetime

def test_mongodb_connection():
    """Test MongoDB connection and basic operations"""
    try:
        app = create_app()
        with app.app_context():
            # Test User operations
            print("Testing User operations...")
            
            # Create a test user
            test_user = User.create_user(
                username="test_user", 
                email="test@example.com", 
                password="test123"
            )
            print(f"✓ Created user: {test_user['username']}")
            
            # Find user by username
            found_user = User.find_by_username("test_user")
            assert found_user is not None, "User not found"
            print(f"✓ Found user by username: {found_user['username']}")
            
            # Test Agent operations
            print("\nTesting Agent operations...")
            
            # Create a test agent
            test_agent = Agent.create_agent(
                name="Test Agent",
                email="agent@example.com",
                country="Test Country",
                user_id=str(test_user['_id'])
            )
            print(f"✓ Created agent: {test_agent['name']}")
            
            # Find agent by email
            found_agent = Agent.find_by_email("agent@example.com")
            assert found_agent is not None, "Agent not found"
            print(f"✓ Found agent by email: {found_agent['name']}")
            
            # Test Booking operations
            print("\nTesting Booking operations...")
            
            # Create a test booking
            test_booking = Booking.create_booking(
                name="Test Booking",
                date_from=datetime(2024, 1, 15),
                date_to=datetime(2024, 1, 20),
                country="Test Country",
                user_id=str(test_user['_id']),
                agent_id=str(test_agent['_id']),
                pax=4
            )
            print(f"✓ Created booking: {test_booking['name']}")
            
            # Find bookings by user
            user_bookings = Booking.find_by_user(test_user['_id'])
            assert len(user_bookings) > 0, "No bookings found for user"
            print(f"✓ Found {len(user_bookings)} booking(s) for user")
            
            # Test data conversion to dict
            print("\nTesting data conversion...")
            user_dict = User.to_dict(test_user)
            agent_dict = Agent.to_dict(test_agent)
            booking_dict = Booking.to_dict(test_booking, test_agent, test_user)
            
            print(f"✓ User dict conversion: {user_dict['username']}")
            print(f"✓ Agent dict conversion: {agent_dict['name']}")
            print(f"✓ Booking dict conversion: {booking_dict['name']}")
            
            # Clean up test data
            print("\nCleaning up test data...")
            User.delete_one({"_id": test_user['_id']})
            Agent.delete_one({"_id": test_agent['_id']})
            Booking.delete_one({"_id": test_booking['_id']})
            print("✓ Test data cleaned up")
            
            print("\n✅ All MongoDB operations working correctly!")
            return True
            
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing MongoDB Migration...")
    print("=" * 50)
    
    if test_mongodb_connection():
        print("\n🎉 Migration test completed successfully!")
        print("\n📋 Next steps:")
        print("1. Install dependencies: pipenv install")
        print("2. Start MongoDB server (if not already running)")
        print("3. Run the Flask application: python run.py")
        print("4. Test the API endpoints with the frontend")
    else:
        print("\n⚠️  Migration test failed. Please check the errors above.")