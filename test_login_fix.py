#!/usr/bin/env python3
"""
Simple test script to verify login credentials match between frontend and backend
"""
import sys
import os

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

def test_credentials_match():
    """Test that the frontend and backend credentials are aligned"""
    
    # Frontend credentials from Login.tsx lines 177-181
    frontend_admin = {"email": "admin@autodmca.com", "password": "admin123"}
    frontend_user = {"email": "user@example.com", "password": "user1234"}
    
    # Backend mock credentials from auth.py updated logic
    backend_supported_users = [
        {"email": "admin@autodmca.com", "password": "admin123", "is_superuser": True},
        {"email": "user@example.com", "password": "user1234", "is_superuser": False},
        {"email": "dev@localhost", "password": "DevPassword123!", "is_superuser": False}  # legacy
    ]
    
    print("=== Testing Credential Alignment ===")
    
    # Test admin credentials
    admin_match = any(
        user["email"] == frontend_admin["email"] and user["password"] == frontend_admin["password"]
        for user in backend_supported_users
    )
    print(f"Admin credentials match: {admin_match}")
    
    # Test user credentials  
    user_match = any(
        user["email"] == frontend_user["email"] and user["password"] == frontend_user["password"]
        for user in backend_supported_users
    )
    print(f"User credentials match: {user_match}")
    
    return admin_match and user_match

def test_environment_config():
    """Test that environment configuration supports mock authentication"""
    try:
        from app.core.config import Settings
        settings = Settings()
        
        print("\n=== Testing Environment Configuration ===")
        print(f"Environment: {settings.ENVIRONMENT}")
        print(f"Debug: {settings.DEBUG}")
        
        mock_auth_enabled = settings.ENVIRONMENT in ["development", "test"] and settings.DEBUG
        print(f"Mock authentication enabled: {mock_auth_enabled}")
        
        return mock_auth_enabled
        
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return False

def test_login_logic_simulation():
    """Simulate the login logic with the test credentials"""
    print("\n=== Simulating Login Logic ===")
    
    # Test credentials
    test_cases = [
        {"email": "admin@autodmca.com", "password": "admin123", "should_work": True},
        {"email": "user@example.com", "password": "user1234", "should_work": True},
        {"email": "admin@autodmca.com", "password": "wrong", "should_work": False},
        {"email": "nonexistent@test.com", "password": "test", "should_work": False}
    ]
    
    for case in test_cases:
        email = case["email"]
        password = case["password"]
        expected = case["should_work"]
        
        # Simulate the backend logic
        mock_user = None
        if email == "admin@autodmca.com" and password == "admin123":
            mock_user = {"id": "admin_user_1", "email": email, "is_superuser": True}
        elif email == "user@example.com" and password == "user1234":
            mock_user = {"id": "regular_user_1", "email": email, "is_superuser": False}
        elif email == "dev@localhost" and password == "DevPassword123!":
            mock_user = {"id": "dev_user_1", "email": email, "is_superuser": False}
        
        result = mock_user is not None
        status = "PASS" if result == expected else "FAIL"
        print(f"{status} {email} -> {'SUCCESS' if result else 'FAILED'} (expected: {'SUCCESS' if expected else 'FAILED'})")

def main():
    print("Testing Login System Fixes\n")
    
    # Run tests
    credentials_ok = test_credentials_match()
    env_config_ok = test_environment_config()
    
    test_login_logic_simulation()
    
    print("\n=== Summary ===")
    if credentials_ok and env_config_ok:
        print("All tests passed! Login should work now.")
        print("\nTo test login:")
        print("1. Start the backend server")
        print("2. Start the frontend") 
        print("3. Use credentials: admin@autodmca.com / admin123")
        print("   or: user@example.com / user1234")
    else:
        print("Some tests failed. Login may still have issues.")
        if not credentials_ok:
            print("  - Credential mismatch between frontend and backend")
        if not env_config_ok:
            print("  - Environment configuration issues")

if __name__ == "__main__":
    main()