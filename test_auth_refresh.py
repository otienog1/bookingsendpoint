# test_auth_refresh.py
# Run this file to test your token refresh implementation

import requests
# import time
# import json
# from datetime import datetime

# Configuration
BASE_URL = "https://bookingsendpoint.onrender.com"  # Change to localhost:5000 for local testing
TEST_USERNAME = "test_user"  # Create this user first
TEST_PASSWORD = "test_password"


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")


def print_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def test_login_without_remember_me():
    """Test standard login without remember me"""
    print("\n1. Testing standard login (no remember me)...")

    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
        "remember_me": False
    })

    if response.status_code == 200:
        data = response.json()
        print_success("Login successful")
        print_info(f"Access token received: {data['token'][:20]}...")
        print_info(f"Refresh token received: {data['refresh_token'][:20]}...")
        return data
    else:
        print_error(f"Login failed: {response.json()}")
        return None


def test_login_with_remember_me():
    """Test login with remember me"""
    print("\n2. Testing login with remember me...")

    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
        "remember_me": True
    })

    if response.status_code == 200:
        data = response.json()
        print_success("Login with remember me successful")
        print_info(f"Access token received: {data['token'][:20]}...")
        print_info(f"Refresh token received: {data['refresh_token'][:20]}...")
        return data
    else:
        print_error(f"Login failed: {response.json()}")
        return None


def test_verify_token(token):
    """Test token verification endpoint"""
    print("\n3. Testing token verification...")

    response = requests.get(f"{BASE_URL}/auth/verify",
                            headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 200:
        data = response.json()
        print_success("Token is valid")
        expires_in = data['expires_in']
        hours = expires_in / 3600
        print_info(f"Token expires in: {hours:.2f} hours")
        return True
    else:
        print_error("Token verification failed")
        return False


def test_refresh_token(refresh_token, remember_me=False):
    """Test token refresh"""
    print("\n4. Testing token refresh...")

    response = requests.post(f"{BASE_URL}/auth/refresh",
                             headers={"Authorization": f"Bearer {refresh_token}"},
                             json={"remember_me": remember_me})

    if response.status_code == 200:
        data = response.json()
        print_success("Token refresh successful")
        print_info(f"New access token: {data['token'][:20]}...")
        return data['token']
    else:
        print_error(f"Token refresh failed: {response.json()}")
        return None


def test_api_call_with_token(token):
    """Test making an authenticated API call"""
    print("\n5. Testing authenticated API call...")

    response = requests.get(f"{BASE_URL}/booking/fetch",
                            headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 200:
        print_success("API call successful")
        data = response.json()
        print_info(f"Fetched {len(data.get('bookings', []))} bookings")
        return True
    else:
        print_error(f"API call failed: {response.status_code}")
        return False


def test_refresh_with_invalid_token():
    """Test refresh with invalid token"""
    print("\n6. Testing refresh with invalid token...")

    response = requests.post(f"{BASE_URL}/auth/refresh",
                             headers={"Authorization": "Bearer invalid_token"})

    if response.status_code == 401:
        print_success("Invalid token correctly rejected")
        return True
    else:
        print_error("Invalid token not rejected properly")
        return False


def test_access_token_as_refresh():
    """Test using access token as refresh token (should fail)"""
    print("\n7. Testing access token used as refresh token...")

    # First login to get tokens
    login_data = test_login_without_remember_me()
    if not login_data:
        return False

    # Try to use access token for refresh
    response = requests.post(f"{BASE_URL}/auth/refresh",
                             headers={"Authorization": f"Bearer {login_data['token']}"})

    if response.status_code == 401:
        print_success("Access token correctly rejected for refresh")
        return True
    else:
        print_error("Access token incorrectly accepted for refresh")
        return False


def run_all_tests():
    """Run all authentication tests"""
    print(f"\n{Colors.BLUE}Running Token Refresh Tests{Colors.END}")
    print("=" * 50)

    # Test 1: Standard login
    login_data = test_login_without_remember_me()
    if not login_data:
        print_error("Cannot continue without successful login")
        return

    # Test 2: Login with remember me
    remember_me_data = test_login_with_remember_me()

    # Test 3: Verify token
    if login_data:
        test_verify_token(login_data['token'])

    # Test 4: Refresh token
    if login_data:
        new_token = test_refresh_token(login_data['refresh_token'])

        # Test 5: Use refreshed token
        if new_token:
            test_api_call_with_token(new_token)

    # Test 6: Invalid refresh token
    test_refresh_with_invalid_token()

    # Test 7: Access token as refresh
    test_access_token_as_refresh()

    print(f"\n{Colors.BLUE}Test Summary{Colors.END}")
    print("=" * 50)
    print_info("All core functionality tests completed")
    print_warning("For full testing, also test token expiry behavior")


def interactive_test():
    """Interactive test for manual verification"""
    print(f"\n{Colors.BLUE}Interactive Token Test{Colors.END}")
    print("=" * 50)

    username = input("Enter username: ")
    password = input("Enter password: ")
    remember = input("Remember me? (y/n): ").lower() == 'y'

    # Login
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": username,
        "password": password,
        "remember_me": remember
    })

    if response.status_code != 200:
        print_error(f"Login failed: {response.json()}")
        return

    data = response.json()
    print_success("Login successful!")

    while True:
        print("\nOptions:")
        print("1. Verify token")
        print("2. Refresh token")
        print("3. Make API call")
        print("4. Decode token (show expiry)")
        print("5. Exit")

        choice = input("\nSelect option: ")

        if choice == '1':
            test_verify_token(data['token'])
        elif choice == '2':
            new_token = test_refresh_token(data['refresh_token'], remember)
            if new_token:
                data['token'] = new_token
        elif choice == '3':
            test_api_call_with_token(data['token'])
        elif choice == '4':
            # This would need JWT library to decode
            print_info("Token details:")
            print(f"Access Token: {data['token'][:50]}...")
            print(f"Refresh Token: {data['refresh_token'][:50]}...")
        elif choice == '5':
            break


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_test()
    else:
        run_all_tests()
        print(
            f"\n{Colors.YELLOW}Tip: Run with 'python test_auth_refresh.py interactive' for manual testing{Colors.END}")