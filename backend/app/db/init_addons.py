"""
Initialize default add-on services in the database
Run this script to populate the database with default add-on services
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.billing.addon_service import initialize_default_addons
from app.db.models.addon_service import AddonService
from app.db.base import Base
from app.db.session import engine

def init_addon_services():
    """Initialize default add-on services"""
    
    # Create tables
    print("Creating addon service tables...")
    Base.metadata.create_all(bind=engine)
    
    # Initialize add-on services
    db = SessionLocal()
    try:
        # Check if addons already exist
        existing_count = db.query(AddonService).count()
        if existing_count > 0:
            print(f"Found {existing_count} existing add-on services. Skipping initialization.")
            return
        
        print("Initializing default add-on services...")
        initialize_default_addons(db)
        
        # Verify creation
        total_addons = db.query(AddonService).count()
        print(f"✅ Successfully created {total_addons} add-on services")
        
        # List created addons
        addons = db.query(AddonService).all()
        print("\nCreated add-on services:")
        for addon in addons:
            price_str = f"${addon.price_monthly}/month" if addon.is_recurring else f"${addon.price_one_time} one-time"
            print(f"  - {addon.name}: {price_str}")
            
    except Exception as e:
        print(f"❌ Error initializing add-on services: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_addon_services()