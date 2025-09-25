#!/usr/bin/env python3
"""
Test script to verify notes functionality in booking models
"""

import os
import sys
from datetime import datetime
import traceback

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_mongodb_notes():
    """Test MongoDB booking model with notes"""
    print("Testing MongoDB Booking model with notes...")
    
    try:
        from app.mongodb_models import Booking, Agent, User
        
        # Test data
        test_notes = "<p>This is a <strong>rich text</strong> note with <em>formatting</em></p>"
        
        # Create a mock booking data
        booking_data = {
            "_id": "test_id",
            "name": "Test Safari Booking",
            "date_from": datetime(2024, 6, 1),
            "date_to": datetime(2024, 6, 7),
            "country": "Kenya",
            "pax": 4,
            "ladies": 2,
            "men": 2,
            "children": 0,
            "teens": 0,
            "agent_id": "test_agent_id",
            "consultant": "Test Consultant",
            "user_id": "test_user_id",
            "notes": test_notes,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # Test to_dict method
        result = Booking.to_dict(booking_data)
        
        if result and "notes" in result:
            print(f"✓ MongoDB to_dict includes notes field: {result['notes'][:50]}...")
            
            if result["notes"] == test_notes:
                print("✓ MongoDB notes field preserved correctly")
                return True
            else:
                print("✗ MongoDB notes field value mismatch")
                return False
        else:
            print("✗ MongoDB to_dict missing notes field")
            return False
            
    except Exception as e:
        print(f"✗ MongoDB test failed: {str(e)}")
        traceback.print_exc()
        return False

def test_sql_notes():
    """Test SQL booking model with notes"""
    print("\nTesting SQL Booking model with notes...")
    
    try:
        from app.booking import Booking
        
        # Test that the model has the notes field
        if hasattr(Booking, 'notes'):
            print("✓ SQL Booking model has notes field")
            
            # Create a mock booking instance
            booking = Booking()
            booking.id = 1
            booking.name = "Test Safari Booking"
            booking.date_from = datetime(2024, 6, 1)
            booking.date_to = datetime(2024, 6, 7)
            booking.country = "Kenya"
            booking.pax = 4
            booking.ladies = 2
            booking.men = 2
            booking.children = 0
            booking.teens = 0
            booking.agent_id = 1
            booking.consultant = "Test Consultant"
            booking.user_id = 1
            booking.notes = "<p>This is a <strong>rich text</strong> note</p>"
            
            # Test to_dict method
            try:
                result = booking.to_dict()
                
                if result and "notes" in result:
                    print(f"✓ SQL to_dict includes notes field: {result['notes'][:50]}...")
                    
                    if result["notes"] == booking.notes:
                        print("✓ SQL notes field preserved correctly")
                        return True
                    else:
                        print("✗ SQL notes field value mismatch")
                        return False
                else:
                    print("✗ SQL to_dict missing notes field")
                    return False
                    
            except Exception as e:
                print(f"✗ SQL to_dict test failed: {str(e)}")
                return False
                
        else:
            print("✗ SQL Booking model missing notes field")
            return False
            
    except Exception as e:
        print(f"✗ SQL test failed: {str(e)}")
        traceback.print_exc()
        return False

def test_create_booking_parameters():
    """Test that create_booking method accepts notes parameter"""
    print("\nTesting create_booking method parameters...")
    
    try:
        from app.mongodb_models import Booking
        import inspect
        
        # Get the method signature
        sig = inspect.signature(Booking.create_booking)
        params = list(sig.parameters.keys())
        
        if 'notes' in params:
            print("✓ create_booking method accepts notes parameter")
            
            # Check if it's optional (has default value)
            notes_param = sig.parameters['notes']
            if notes_param.default is None:
                print("✓ notes parameter is optional with None default")
                return True
            else:
                print(f"? notes parameter default: {notes_param.default}")
                return True
        else:
            print("✗ create_booking method missing notes parameter")
            print(f"Available parameters: {params}")
            return False
            
    except Exception as e:
        print(f"✗ Parameter test failed: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("Testing Notes Functionality in Booking Models")
    print("=" * 50)
    
    results = []
    
    # Test MongoDB model
    results.append(test_mongodb_notes())
    
    # Test SQL model
    results.append(test_sql_notes())
    
    # Test method parameters
    results.append(test_create_booking_parameters())
    
    print("\n" + "=" * 50)
    print("Test Results:")
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())