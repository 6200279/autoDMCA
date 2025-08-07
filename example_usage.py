"""
Example usage of the AutoDMCA Content Scanning Engine
"""

import asyncio
from scanning.scanner import ContentScanner
from scanning.config import ScannerConfig, ScannerSettings


async def main():
    """Example of how to use the content scanning engine."""
    
    # 1. Configure the scanner
    settings = ScannerSettings(
        # Search API keys
        google_api_key="your-google-api-key",
        google_search_engine_id="your-search-engine-id",
        bing_api_key="your-bing-api-key",
        
        # Database and Redis
        database_url="postgresql://user:pass@localhost/autodmca",
        redis_url="redis://localhost:6379/0",
        
        # Rate limiting
        requests_per_minute=60,
        concurrent_requests=10,
        
        # Face recognition settings
        face_recognition_tolerance=0.6,
        similarity_threshold=0.85,
        
        # DMCA settings
        dmca_sender_email="takedown@yourdomain.com",
        dmca_sender_name="Your Company Legal Team"
    )
    
    config = ScannerConfig(settings=settings)
    
    # 2. Create and initialize scanner
    scanner = ContentScanner(config)
    await scanner.initialize()
    
    try:
        # 3. Add a person to monitor
        success = await scanner.add_person(
            person_id="creator_123",
            reference_images=[
                "https://example.com/creator/photo1.jpg",
                "https://example.com/creator/photo2.jpg"
            ],
            usernames=[
                "creator_username",
                "creator_onlyfans", 
                "creator_ig"
            ],
            email="creator@example.com",
            additional_keywords=["premium", "exclusive"],
            scan_interval_hours=12,  # Scan every 12 hours
            priority_protection=True  # Enable priority scanning
        )
        
        print(f"Person added successfully: {success}")
        
        # 4. Trigger an immediate scan
        task_id = await scanner.trigger_immediate_scan(
            person_id="creator_123",
            scan_type="full",
            priority=True
        )
        print(f"Immediate scan triggered: {task_id}")
        
        # 5. Check person status
        status = await scanner.get_person_status("creator_123")
        print(f"Person status: {status}")
        
        # 6. Check DMCA queue status
        dmca_status = await scanner.get_dmca_status()
        print(f"DMCA queue status: {dmca_status}")
        
        # 7. Get system health
        health = await scanner.get_system_health()
        print(f"System health: {health['system_status']}")
        
        # 8. Manual URL scan
        matches = await scanner.manual_scan_url(
            url="https://suspicious-site.com/leaked-content",
            person_id="creator_123"
        )
        print(f"Manual scan found {len(matches)} matches")
        
        # 9. Export person data (for GDPR compliance)
        export_data = await scanner.export_person_data("creator_123")
        print(f"Data exported for person: {export_data['person_id']}")
        
        # 10. Run scanner in background (optional)
        # await scanner.run_forever()  # This runs until interrupted
        
    finally:
        # Clean up
        await scanner.close()


async def simple_usage():
    """Simple usage example with minimal configuration."""
    
    # Create scanner with default settings
    scanner = ContentScanner()
    await scanner.initialize()
    
    try:
        # Add person with minimal info
        await scanner.add_person(
            person_id="simple_user",
            reference_images=["path/to/reference.jpg"],
            usernames=["username"],
            email="user@example.com"
        )
        
        # Trigger scan
        task_id = await scanner.trigger_immediate_scan("simple_user")
        print(f"Scan started: {task_id}")
        
        # Check status after some time
        await asyncio.sleep(60)  # Wait 1 minute
        
        status = await scanner.get_person_status("simple_user")
        print(f"Protection active: {status.get('protection_active', False)}")
        
    finally:
        await scanner.close()


if __name__ == "__main__":
    # Run the example
    print("AutoDMCA Content Scanner Example")
    print("=================================")
    
    # Choose which example to run
    choice = input("Run (1) full example or (2) simple example? [1/2]: ")
    
    if choice == "2":
        asyncio.run(simple_usage())
    else:
        asyncio.run(main())