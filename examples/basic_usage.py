"""
Basic Usage Example for AutoDMCA System

This example demonstrates how to use the AutoDMCA system to process
DMCA takedown requests with complete workflow automation.
"""

import asyncio
import os
from datetime import datetime
from uuid import uuid4

# Import AutoDMCA components
from src.autodmca.models.takedown import TakedownRequest, CreatorProfile, InfringementData
from src.autodmca.models.hosting import DMCAAgent
from src.autodmca.services.whois_service import WHOISService
from src.autodmca.services.email_service import EmailService
from src.autodmca.services.search_delisting_service import SearchDelistingService
from src.autodmca.services.dmca_service import DMCAService, DMCAServiceConfig
from src.autodmca.utils.cache import CacheManager
from src.autodmca.utils.rate_limiter import RateLimiter


async def main():
    """Main example function demonstrating AutoDMCA usage."""
    
    print("🔧 AutoDMCA System - Basic Usage Example")
    print("=" * 50)
    
    # Step 1: Configure the system
    print("\n1. Setting up DMCA agent and services...")
    
    # Create DMCA agent (this represents your legal service)
    dmca_agent = DMCAAgent(
        name="AutoDMCA Legal Services",
        title="DMCA Agent", 
        organization="AutoDMCA Inc.",
        email="legal@autodmca.com",
        phone="+1-555-DMCA-LAW",
        address_line1="123 Legal Avenue",
        city="Copyright City",
        state_province="CA",
        postal_code="90210",
        country="USA"
    )
    
    # Initialize services
    cache_manager = CacheManager()
    rate_limiter = RateLimiter(max_calls=60, time_window=60)
    
    whois_service = WHOISService(
        cache_manager=cache_manager,
        rate_limiter=rate_limiter
    )
    
    email_service = EmailService(
        sendgrid_api_key=os.getenv("SENDGRID_API_KEY"),
        smtp_config={
            'host': os.getenv("SMTP_HOST", "smtp.gmail.com"),
            'port': int(os.getenv("SMTP_PORT", "587")),
            'username': os.getenv("SMTP_USERNAME"),
            'password': os.getenv("SMTP_PASSWORD")
        },
        cache_manager=cache_manager,
        rate_limiter=rate_limiter
    )
    
    search_delisting_service = SearchDelistingService(
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        google_custom_search_id=os.getenv("GOOGLE_SEARCH_ENGINE_ID"),
        bing_api_key=os.getenv("BING_API_KEY"),
        cache_manager=cache_manager,
        rate_limiter=rate_limiter
    )
    
    # Configure DMCA service
    config = DMCAServiceConfig(
        max_concurrent_requests=5,
        followup_interval_days=7,
        max_followup_attempts=3,
        auto_search_delisting=True,
        search_delisting_delay_hours=72,
        enable_anonymity=True
    )
    
    # Create main DMCA service
    dmca_service = DMCAService(
        whois_service=whois_service,
        email_service=email_service,
        search_delisting_service=search_delisting_service,
        agent_contact=dmca_agent,
        config=config,
        cache_manager=cache_manager,
        rate_limiter=rate_limiter
    )
    
    print("✅ Services configured successfully!")
    
    # Step 2: Create a creator profile (with anonymity)
    print("\n2. Creating creator profile with anonymity protection...")
    
    creator_profile = CreatorProfile(
        public_name="Creative Artist",  # Pseudonym/stage name
        business_name="Creative Art Studio LLC",
        email="artist@creativeartist.com",
        phone="+1-555-ART-WORK",
        address_line1="456 Artist Lane",
        city="Creative City", 
        state_province="CA",
        postal_code="90211",
        country="USA",
        protected_usernames=["creativeartist", "artist_official", "creative_art"],
        platform_urls=[
            "https://creativeartist.com",
            "https://onlyfans.com/creativeartist",
            "https://patreon.com/creativeartist"
        ],
        use_anonymity=True,  # Enable anonymity protection
        agent_representation=True  # Use agent for all communications
    )
    
    print(f"✅ Creator profile created: {creator_profile.public_name}")
    print(f"   Anonymity enabled: {creator_profile.use_anonymity}")
    print(f"   Protected usernames: {len(creator_profile.protected_usernames)}")
    
    # Step 3: Define infringement data
    print("\n3. Defining copyright infringement details...")
    
    infringement_data = InfringementData(
        infringing_url="https://pirate-site.example.com/stolen/my-artwork.jpg",
        description="Unauthorized use of my copyrighted digital artwork without permission, credit, or compensation",
        original_work_title="Digital Abstract Masterpiece #47",
        original_work_description="Original digital artwork created using advanced digital painting techniques",
        original_work_urls=[
            "https://creativeartist.com/gallery/abstract-47",
            "https://creativeartist.com/portfolio/digital-art"
        ],
        content_type="image",
        copyright_registration_number="VA0002345678",  # Optional
        creation_date=datetime(2023, 6, 15),
        publication_date=datetime(2023, 6, 20),
        detected_by="automated_content_scanner",
        confidence_score=0.95,
        screenshot_url="https://evidence.autodmca.com/screenshot-12345.jpg"
    )
    
    print(f"✅ Infringement defined:")
    print(f"   Infringing URL: {infringement_data.infringing_url}")
    print(f"   Original work: {infringement_data.original_work_title}")
    print(f"   Confidence: {infringement_data.confidence_score * 100}%")
    
    # Step 4: Create takedown request
    print("\n4. Creating DMCA takedown request...")
    
    takedown_request = TakedownRequest(
        creator_id=uuid4(),  # Usually from your user database
        creator_profile=creator_profile,
        infringement_data=infringement_data,
        priority=8  # High priority (1-10 scale)
    )
    
    print(f"✅ Takedown request created:")
    print(f"   Request ID: {takedown_request.id}")
    print(f"   Status: {takedown_request.status.value}")
    print(f"   Priority: {takedown_request.priority}/10")
    
    # Step 5: Process the takedown request
    print("\n5. Processing DMCA takedown request...")
    print("   This includes:")
    print("   - WHOIS lookup to identify hosting provider")
    print("   - Generate legally compliant DMCA notice")
    print("   - Send notice via email with delivery tracking")
    print("   - Schedule search engine delisting (optional)")
    print("   - Set up follow-up monitoring")
    
    try:
        # Process the takedown request through the complete workflow
        result = await dmca_service.process_takedown_request(takedown_request)
        
        if result['success']:
            print("\n✅ Takedown request processed successfully!")
            print(f"   Hosting provider: {result.get('hosting_provider', 'Unknown')}")
            print(f"   Email sent: {result.get('email_sent', False)}")
            print(f"   Message ID: {result.get('message_id', 'N/A')}")
            print(f"   Search delisting scheduled: {result.get('search_delisting_scheduled', False)}")
            print(f"   Final status: {takedown_request.status.value}")
        else:
            print(f"\n❌ Takedown processing failed: {result['message']}")
            return
            
    except Exception as e:
        print(f"\n❌ Error processing takedown: {str(e)}")
        return
    
    # Step 6: Check status and demonstrate follow-up
    print("\n6. Monitoring takedown status...")
    
    status_info = await dmca_service.check_takedown_status(takedown_request)
    
    print(f"   Current status: {status_info['current_status']}")
    print(f"   Email sent: {status_info['email_sent']}")
    print(f"   Follow-up count: {status_info['followup_count']}")
    print(f"   Next action: {status_info['next_action']}")
    
    if status_info.get('needs_followup'):
        print(f"   ⏰ Follow-up needed!")
    
    # Step 7: Demonstrate manual follow-up (if needed)
    print("\n7. Demonstrating follow-up process...")
    
    # Simulate that some time has passed and we need to send a follow-up
    if takedown_request.notice_sent_at:
        print("   Simulating follow-up scenario...")
        
        # For demo purposes, we'll just show how to send a follow-up
        # In reality, you'd check if follow-up is actually needed
        print("   Would send follow-up notice if no response received")
        
        # Example of sending follow-up (commented out to avoid actual sending)
        # followup_result = await dmca_service.send_followup(takedown_request)
        # print(f"   Follow-up result: {followup_result['success']}")
    
    # Step 8: Demonstrate search delisting
    print("\n8. Demonstrating search engine delisting...")
    
    # Request delisting from Google and Bing
    delisting_result = await dmca_service.request_search_delisting(
        [takedown_request],
        ["google", "bing"]  # Search engines
    )
    
    if delisting_result['success']:
        print("   ✅ Search delisting requests submitted!")
        for engine, result in delisting_result['results'].items():
            print(f"   - {engine.capitalize()}: {result.get('submitted_count', 0)} URLs submitted")
    else:
        print(f"   ❌ Search delisting failed: {delisting_result.get('error', 'Unknown error')}")
    
    # Step 9: Show service metrics
    print("\n9. Service performance metrics...")
    
    metrics = await dmca_service.get_service_metrics()
    
    print(f"   Total requests processed: {metrics['total_requests']}")
    print(f"   Successful takedowns: {metrics['successful_takedowns']}")
    print(f"   Failed takedowns: {metrics['failed_takedowns']}")
    print(f"   Success rate: {metrics['success_rate']:.1f}%")
    print(f"   Emails sent: {metrics['emails_sent']}")
    print(f"   Active requests: {metrics['active_requests']}")
    
    print("\n🎉 AutoDMCA Example completed successfully!")
    print("\nNext steps:")
    print("- Set up environment variables for API keys")
    print("- Configure your database for persistent storage")
    print("- Set up webhook endpoints for email responses")
    print("- Implement automated scanning for new infringements")
    print("- Add monitoring and alerting for the service")


async def batch_processing_example():
    """Example of batch processing multiple takedown requests."""
    
    print("\n" + "="*60)
    print("🔄 BATCH PROCESSING EXAMPLE")
    print("="*60)
    
    # This would use the same services configured above
    # For brevity, we'll just show the concept
    
    from src.autodmca.models.takedown import TakedownBatch
    
    print("\n1. Creating multiple takedown requests...")
    
    # Create sample creator profile
    creator_profile = CreatorProfile(
        public_name="Batch Creator",
        email="batch@example.com",
        address_line1="123 Batch St",
        city="Batch City",
        state_province="CA", 
        postal_code="12345",
        country="USA",
        use_anonymity=True
    )
    
    # Create multiple infringement cases
    requests = []
    for i in range(5):
        infringement = InfringementData(
            infringing_url=f"https://pirate-site.com/stolen-{i}.jpg",
            description=f"Unauthorized use of artwork #{i}",
            original_work_title=f"Original Artwork #{i}",
            original_work_description=f"Description for artwork {i}",
            content_type="image"
        )
        
        request = TakedownRequest(
            creator_id=uuid4(),
            creator_profile=creator_profile,
            infringement_data=infringement,
            priority=5 + i  # Varying priorities
        )
        requests.append(request)
    
    # Create batch
    batch = TakedownBatch(
        creator_id=uuid4(),
        requests=requests,
        priority=7
    )
    
    print(f"✅ Created batch with {len(batch.requests)} requests")
    print(f"   Batch ID: {batch.batch_id}")
    print(f"   Batch priority: {batch.priority}")
    
    # Show batch status
    status_summary = batch.get_status_summary()
    print(f"\n   Status summary:")
    for status, count in status_summary.items():
        print(f"   - {status.value}: {count}")
    
    print(f"   Completion rate: {batch.completion_rate:.1f}%")
    print(f"   Is complete: {batch.is_complete}")
    
    print("\n   In a real implementation, you would:")
    print("   - Process batch with: dmca_service.process_batch_takedowns(batch)")
    print("   - Monitor progress with real-time updates")
    print("   - Handle failures and retries automatically")


if __name__ == "__main__":
    """Run the example."""
    
    print("Starting AutoDMCA Basic Usage Example...")
    
    # Note: Make sure to set your environment variables:
    # SENDGRID_API_KEY, SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD,
    # GOOGLE_API_KEY, GOOGLE_SEARCH_ENGINE_ID, BING_API_KEY
    
    try:
        # Run main example
        asyncio.run(main())
        
        # Run batch processing example
        asyncio.run(batch_processing_example())
        
    except KeyboardInterrupt:
        print("\n⏹️  Example interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {str(e)}")
        print("Make sure all dependencies are installed and environment variables are set")
    
    print("\nThank you for trying AutoDMCA! 🚀")