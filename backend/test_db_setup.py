#!/usr/bin/env python3
"""
Test script to verify database setup and configuration fixes.
"""

import os
import sys
from pathlib import Path

# Add the app directory to Python path
app_path = Path(__file__).parent / "app"
sys.path.insert(0, str(app_path))

def test_configuration():
    """Test configuration loading."""
    print("Testing configuration...")
    
    try:
        from core.config import settings
        
        print(f"[OK] Configuration loaded successfully")
        print(f"  - Project: {settings.PROJECT_NAME}")
        print(f"  - Version: {settings.VERSION}")
        print(f"  - Database URI configured: {bool(settings.SQLALCHEMY_DATABASE_URI)}")
        print(f"  - SSL Mode: {settings.POSTGRES_SSL_MODE}")
        print(f"  - Connect Timeout: {settings.POSTGRES_CONNECT_TIMEOUT}")
        print(f"  - Debug Mode: {settings.DEBUG}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Configuration test failed: {e}")
        return False


def test_requirements():
    """Test database driver requirements."""
    print("\nTesting database driver availability...")
    
    drivers_tested = []
    
    # Test asyncpg
    try:
        import asyncpg
        drivers_tested.append(("asyncpg", "[OK] Available", asyncpg.__version__))
    except ImportError:
        drivers_tested.append(("asyncpg", "[MISSING] Not installed (install with: pip install asyncpg)", "N/A"))
    
    # Test psycopg3
    try:
        import psycopg
        drivers_tested.append(("psycopg (v3)", "[OK] Available", psycopg.__version__))
    except ImportError:
        drivers_tested.append(("psycopg (v3)", "[MISSING] Not installed (install with: pip install psycopg[binary])", "N/A"))
    
    # Test psycopg2cffi
    try:
        import psycopg2cffi
        drivers_tested.append(("psycopg2cffi", "[OK] Available", psycopg2cffi.__version__))
    except ImportError:
        drivers_tested.append(("psycopg2cffi", "[MISSING] Not installed (install with: pip install psycopg2cffi)", "N/A"))
    
    # Test old psycopg2
    try:
        import psycopg2
        drivers_tested.append(("psycopg2 (legacy)", "[WARNING] Available (may cause issues on Windows)", psycopg2.__version__))
    except ImportError:
        drivers_tested.append(("psycopg2 (legacy)", "[OK] Not installed (good - replaced with better alternatives)", "N/A"))
    
    for driver, status, version in drivers_tested:
        print(f"  - {driver}: {status} (version: {version})")
    
    # Check if at least one driver is available
    available_drivers = [d for d in drivers_tested if "[OK] Available" in d[1]]
    if available_drivers:
        print(f"\n[OK] {len(available_drivers)} PostgreSQL driver(s) available")
        return True
    else:
        print("\n[FAIL] No PostgreSQL drivers available")
        return False


def test_connection_string():
    """Test connection string generation."""
    print("\nTesting database connection string generation...")
    
    try:
        from core.config import settings
        
        uri = settings.SQLALCHEMY_DATABASE_URI
        print(f"[OK] Database URI generated: {uri[:50]}...")
        
        # Verify URI components
        if "postgresql+asyncpg://" in uri:
            print("[OK] Using asyncpg driver")
        elif "postgresql+psycopg://" in uri:
            print("[OK] Using psycopg3 driver")
        else:
            print("[WARNING] Using different driver")
        
        if "sslmode=" in uri:
            print("[OK] SSL configuration included")
        
        if "application_name=" in uri:
            print("[OK] Application name included")
        
        if "connect_timeout=" in uri:
            print("[OK] Connection timeout configured")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Connection string test failed: {e}")
        return False


def test_imports():
    """Test critical imports without database connection."""
    print("\nTesting critical module imports...")
    
    try:
        # Test SQLAlchemy async support
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        print("[OK] SQLAlchemy async imports successful")
        
        # Test Alembic
        from alembic import command
        from alembic.config import Config
        print("[OK] Alembic imports successful")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Import test failed: {e}")
        return False


def print_recommendations():
    """Print setup recommendations."""
    print("\n" + "="*60)
    print("SETUP RECOMMENDATIONS")
    print("="*60)
    
    print("\n1. Install Required Packages:")
    print("   pip install -r requirements.txt")
    print("   # Or individually:")
    print("   pip install asyncpg psycopg[binary] psycopg2cffi")
    
    print("\n2. Database Setup:")
    print("   # Using Docker (recommended for development):")
    print("   docker-compose up postgres -d")
    print("   # Or install PostgreSQL locally")
    
    print("\n3. Environment Configuration:")
    print("   # Copy .env.example to .env and configure:")
    print("   POSTGRES_SERVER=localhost")
    print("   POSTGRES_USER=postgres")
    print("   POSTGRES_PASSWORD=your-password")
    print("   POSTGRES_DB=autodmca")
    
    print("\n4. Run Database Migrations:")
    print("   python -m app.db.startup init")
    print("   # Or manually:")
    print("   alembic upgrade head")
    
    print("\n5. Test Connection:")
    print("   python -m app.db.startup check")
    
    print("\n6. Start Application:")
    print("   uvicorn app.main:app --reload")


def main():
    """Run all tests."""
    print("Database Setup Verification")
    print("="*50)
    
    tests = [
        test_configuration,
        test_requirements,
        test_connection_string,
        test_imports
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"[ERROR] Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("[SUCCESS] All tests passed! Database setup is configured correctly.")
    elif passed > 0:
        print("[WARNING] Partial success. Some components are working.")
        print("  Install missing dependencies and check configuration.")
    else:
        print("[FAIL] Setup verification failed. Check configuration and dependencies.")
    
    print_recommendations()
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)