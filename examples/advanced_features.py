"""
Advanced Features Example for AutoDMCA System

This example demonstrates advanced features including:
- Response handling and counter-notice processing
- Anonymity protection and security features
- Custom templates and validation
- Performance monitoring and analytics
- Error handling and recovery
"""

import asyncio
import os
from datetime import datetime, timedelta
from uuid import uuid4

from src.autodmca.models.takedown import TakedownRequest, CreatorProfile, InfringementData
from src.autodmca.models.hosting import DMCAAgent, HostingProvider, ContactInfo
from src.autodmca.services.response_handler import ResponseHandler, ResponseType
from src.autodmca.templates.template_renderer import TemplateRenderer
from src.autodmca.utils.security import AnonymityHelper
from src.autodmca.utils.validators import EmailValidator, URLValidator
from src.autodmca.utils.cache import CacheManager
from src.autodmca.services.email_service import EmailService


async def response_handling_example():
    """Demonstrate advanced response handling features."""
    
    print("🔄 RESPONSE HANDLING & COUNTER-NOTICE PROCESSING")
    print("=" * 55)
    
    # Initialize response handler
    email_service = EmailService()
    response_handler = ResponseHandler(email_service)
    
    print("\n1. Processing different types of responses...")
    
    # Example responses to classify
    test_responses = [
        {
            'content': 'Thank you for your DMCA notice. We have received your complaint and assigned reference number DMCA-2023-001.',
            'subject': 'DMCA Notice Received - Ref: DMCA-2023-001',
            'sender': 'dmca@hosting-provider.com',
            'expected_type': ResponseType.ACKNOWLEDGMENT
        },
        {
            'content': 'The content has been successfully removed from our platform as requested in your DMCA notice.',
            'subject': 'Content Removed - DMCA Compliance',
            'sender': 'abuse@hosting-provider.com', 
            'expected_type': ResponseType.TAKEDOWN_COMPLETE
        },
        {
            'content': '''This is a counter-notice pursuant to Section 512(g) of the DMCA.
            I have a good faith belief that the material was removed by mistake.
            I consent to jurisdiction of Federal District Court.
            I swear, under penalty of perjury, that this information is accurate.
            
            John Doe
            john.doe@example.com
            (555) 123-4567''',
            'subject': 'Counter-Notice for DMCA Takedown',
            'sender': 'user@example.com',
            'expected_type': ResponseType.COUNTER_NOTICE
        },
        {
            'content': 'We cannot remove the requested content as it appears to qualify as fair use under copyright law.',
            'subject': 'DMCA Request Denied',
            'sender': 'legal@hosting-provider.com',
            'expected_type': ResponseType.REJECTION
        }
    ]
    
    for i, response in enumerate(test_responses, 1):
        print(f"\n   Response {i}: {response['expected_type']}")
        
        classification = response_handler._classify_response(
            response['content'], 
            response['subject']
        )
        
        print(f"   ✅ Detected type: {classification['type']}")
        print(f"   📊 Confidence: {classification['confidence']:.1%}")
        
        if classification['type'] == ResponseType.COUNTER_NOTICE:
            print("   ⚠️  Counter-notice detected - requires special handling!")
            counter_info = response_handler._parse_counter_notice(response['content'])
            print(f"   📋 Has required elements: {counter_info.get('has_required_elements', False)}")
            print(f"   📧 Contact email: {counter_info.get('subscriber_info', {}).get('email', 'Not found')}")
    
    print("\n2. Counter-notice processing workflow...")
    print("   When a counter-notice is received:")
    print("   - System validates required DMCA elements")
    print("   - Extracts subscriber contact information")
    print("   - Notifies original complainant")
    print("   - Starts 10-14 day legal response period")
    print("   - Tracks resolution status")


async def anonymity_protection_example():
    """Demonstrate anonymity protection and security features."""
    
    print("\n🔒 ANONYMITY PROTECTION & SECURITY FEATURES")
    print("=" * 50)
    
    # Create DMCA agent for anonymity
    dmca_agent = DMCAAgent(
        name="Privacy Protection Services LLC",
        title="DMCA Agent",
        organization="Privacy Protection Services LLC",
        email="dmca@privacyprotection.com",
        phone="+1-555-PRIVACY",
        address_line1="789 Privacy Boulevard",
        city="Secure City",
        state_province="NV",
        postal_code="89101",
        country="USA"
    )
    
    anonymity_helper = AnonymityHelper(dmca_agent)
    
    print("\n1. Creator profile anonymization...")
    
    # Create creator profile with real information
    creator_profile = CreatorProfile(
        public_name="Sarah ContentCreator",  # Pseudonym
        email="sarah@realemailaddress.com",  # Real email (to be protected)
        phone="+1-555-REAL-NUM",            # Real phone (to be protected)
        address_line1="123 Real Street",     # Real address (to be protected)
        city="Real City",
        state_province="CA",
        postal_code="90210",
        country="USA",
        protected_usernames=["sarahcreates", "sarah_official"],
        use_anonymity=True,
        agent_representation=True
    )
    
    # Anonymize for external use
    anonymized_contact = anonymity_helper.anonymize_creator_profile(creator_profile)
    
    print("   Original creator info (PROTECTED):")
    print(f"   - Real email: {creator_profile.email} → HIDDEN")
    print(f"   - Real phone: {creator_profile.phone} → HIDDEN") 
    print(f"   - Real address: {creator_profile.city}, {creator_profile.state_province} → HIDDEN")
    
    print("\n   Anonymized contact info (PUBLIC):")
    print(f"   - Public name: {anonymized_contact['public_name']}")
    print(f"   - Contact name: {anonymized_contact['contact_name']}")
    print(f"   - Contact email: {anonymized_contact['contact_email']}")
    print(f"   - Authorized agent: {anonymized_contact['is_authorized_agent']}")
    
    print("\n2. Pseudonym validation...")
    
    test_names = [
        "Sarah ContentCreator",    # Good pseudonym
        "Dr. Sarah Johnson III",   # Might reveal real identity  
        "Sarah123",               # Numbers might be personal
        "S",                      # Too short
    ]
    
    for name in test_names:
        validation = anonymity_helper.validate_pseudonym(name)
        status = "✅" if validation['is_valid'] else "⚠️"
        print(f"   {status} '{name}': Valid={validation['is_valid']}, Pseudonym-like={validation['is_pseudonym']}")
        
        if validation['warnings']:
            for warning in validation['warnings']:
                print(f"      ⚠️  {warning}")
    
    print("\n3. Privacy risk assessment...")
    
    # Sample DMCA notice content
    dmca_content = f"""
    I am the copyright owner of the work titled "Digital Art Piece".
    The infringing content can be found at: https://pirate-site.com/stolen.jpg
    My original work is located at: https://sarahcreates.com/portfolio/art-piece
    
    Please remove this content immediately.
    
    Best regards,
    {creator_profile.public_name}
    {anonymized_contact['contact_email']}
    """
    
    risk_assessment = anonymity_helper.assess_privacy_risk(creator_profile, dmca_content)
    
    print(f"   Overall privacy risk: {risk_assessment['overall_risk'].upper()}")
    print(f"   Privacy score: {risk_assessment['privacy_score']}/100")
    
    if risk_assessment['risks_found']:
        print("   🚨 Risks identified:")
        for risk in risk_assessment['risks_found']:
            print(f"      - {risk}")
    
    if risk_assessment['recommendations']:
        print("   💡 Recommendations:")
        for rec in risk_assessment['recommendations']:
            print(f"      - {rec}")
    
    print("\n4. Anonymity compliance checklist...")
    
    checklist = anonymity_helper.get_anonymity_checklist(creator_profile)
    
    print(f"   Compliance score: {checklist['compliance_percentage']:.1f}%")
    print("   Checklist items:")
    
    for item in checklist['items']:
        status = "✅" if item['status'] == 'pass' else "❌"
        requirement = " (REQUIRED)" if item['required'] else ""
        print(f"   {status} {item['description']}{requirement}")


async def template_customization_example():
    """Demonstrate custom template features and validation."""
    
    print("\n📝 TEMPLATE CUSTOMIZATION & VALIDATION")
    print("=" * 45)
    
    template_renderer = TemplateRenderer()
    
    print("\n1. Template validation...")
    
    # Test template with various issues
    test_template = """
    Dear {{ recipient_name }},
    
    We are writing regarding {{ original_work_title }} found at {{ infringing_url }}.
    Please contact {{ creator_email }} for resolution.
    
    Invalid URL: {{ malformed_url }}
    Invalid email: {{ bad_email }}
    """
    
    test_variables = {
        'recipient_name': 'Support Team',
        'original_work_title': 'My Artwork',
        'infringing_url': 'https://example.com/stolen.jpg',
        'creator_email': 'valid@example.com',
        'malformed_url': 'not-a-valid-url',
        'bad_email': 'invalid-email-format'
    }
    
    from src.autodmca.templates.dmca_notice import DMCANoticeTemplate
    
    errors = DMCANoticeTemplate.validate_template_variables(test_template, test_variables)
    
    if errors:
        print("   ❌ Template validation errors found:")
        for field, error in errors.items():
            print(f"      - {field}: {error}")
    else:
        print("   ✅ Template validation passed!")
    
    print("\n2. Legal compliance validation...")
    
    # Create a sample takedown request for testing
    creator_profile = CreatorProfile(
        public_name="Test Creator",
        email="creator@example.com",
        address_line1="123 Test St",
        city="Test City",
        state_province="CA",
        postal_code="12345",
        country="USA"
    )
    
    infringement_data = InfringementData(
        infringing_url="https://example.com/test.jpg",
        description="Test infringement",
        original_work_title="Test Work",
        original_work_description="Test description",
        content_type="image"
    )
    
    takedown_request = TakedownRequest(
        creator_id=uuid4(),
        creator_profile=creator_profile,
        infringement_data=infringement_data
    )
    
    # Render and validate notice
    rendered_notice = template_renderer.render_dmca_notice(takedown_request)
    validation_warnings = template_renderer.validate_rendered_notice(rendered_notice)
    
    print(f"   Rendered notice length: {len(rendered_notice['body'])} characters")
    
    if validation_warnings:
        print("   ⚠️  Validation warnings:")
        for warning in validation_warnings:
            print(f"      - {warning}")
    else:
        print("   ✅ Legal compliance validation passed!")
    
    print("\n3. Custom template filters...")
    
    # Demonstrate custom template filters
    print("   Available filters:")
    print("   - format_date: Format datetime objects")
    print("   - format_address: Format multi-line addresses") 
    print("   - sanitize_text: Remove potentially dangerous content")
    print("   - truncate_url: Shorten long URLs for display")
    
    test_date = datetime.now()
    formatted_date = template_renderer._format_date(test_date)
    print(f"   Date formatting example: {test_date} → {formatted_date}")
    
    long_url = "https://very-long-domain-name.example.com/very/long/path/to/content.jpg"
    truncated = template_renderer._truncate_url(long_url, 40)
    print(f"   URL truncation example: {truncated}")


async def performance_monitoring_example():
    """Demonstrate performance monitoring and analytics."""
    
    print("\n📊 PERFORMANCE MONITORING & ANALYTICS")
    print("=" * 45)
    
    print("\n1. Hosting provider performance tracking...")
    
    # Create sample hosting provider with performance data
    hosting_provider = HostingProvider(
        name="Example Hosting",
        domain="example-host.com",
        abuse_email="abuse@example-host.com",
        is_dmca_compliant=True
    )
    
    # Simulate performance updates
    performance_scenarios = [
        (True, 2),   # Success in 2 days
        (True, 1),   # Success in 1 day
        (False, 14), # Failed after 14 days
        (True, 3),   # Success in 3 days
        (True, 2),   # Success in 2 days
    ]
    
    print("   Simulating takedown attempts:")
    for i, (success, days) in enumerate(performance_scenarios, 1):
        hosting_provider.update_performance(success, days)
        result = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"   Attempt {i}: {result} in {days} days")
    
    print(f"\n   📈 Performance Summary:")
    print(f"   - Success rate: {hosting_provider.success_rate:.1f}%")
    print(f"   - Average response time: {hosting_provider.average_response_days} days")
    print(f"   - Total notices sent: {hosting_provider.total_notices_sent}")
    print(f"   - Reliability rating: {'✅ RELIABLE' if hosting_provider.is_reliable() else '⚠️  UNRELIABLE'}")
    
    print("\n2. Email delivery tracking...")
    
    email_service = EmailService()
    
    # Simulate delivery validation
    test_emails = [
        "valid@gmail.com",
        "business@company.com", 
        "invalid-email",
        "test@10minutemail.com",  # Disposable
    ]
    
    print("   Email validation results:")
    for email in test_emails:
        result = await email_service.validate_email_deliverability(email)
        status = "✅" if result['valid'] and result['deliverable'] else "❌"
        print(f"   {status} {email}: Valid={result['valid']}, Deliverable={result.get('deliverable', 'Unknown')}")
    
    print("\n3. Service health monitoring...")
    
    # Simulate service metrics
    sample_metrics = {
        'total_requests': 150,
        'successful_takedowns': 142,
        'failed_takedowns': 8,
        'emails_sent': 150,
        'search_delistings': 45,
        'followups_sent': 23,
        'active_requests': 12
    }
    
    success_rate = (sample_metrics['successful_takedowns'] / sample_metrics['total_requests']) * 100
    
    print(f"   📊 Service Metrics:")
    print(f"   - Total requests processed: {sample_metrics['total_requests']}")
    print(f"   - Success rate: {success_rate:.1f}%")
    print(f"   - Active requests: {sample_metrics['active_requests']}")
    print(f"   - Follow-up rate: {(sample_metrics['followups_sent'] / sample_metrics['total_requests'] * 100):.1f}%")
    
    # Health assessment
    if success_rate >= 90:
        health = "🟢 EXCELLENT"
    elif success_rate >= 80:
        health = "🟡 GOOD"
    else:
        health = "🔴 NEEDS ATTENTION"
    
    print(f"   Overall service health: {health}")


async def error_handling_example():
    """Demonstrate error handling and recovery mechanisms."""
    
    print("\n🛡️  ERROR HANDLING & RECOVERY")
    print("=" * 35)
    
    print("\n1. Input validation and sanitization...")
    
    url_validator = URLValidator()
    email_validator = EmailValidator()
    
    # Test various inputs
    test_cases = [
        {
            'type': 'URL',
            'value': 'https://legitimate-site.com/content.jpg',
            'validator': url_validator.validate
        },
        {
            'type': 'URL',
            'value': 'http://suspicious-site.tk/malware.exe', 
            'validator': url_validator.validate
        },
        {
            'type': 'Email',
            'value': 'legitimate@business.com',
            'validator': email_validator.validate
        },
        {
            'type': 'Email',
            'value': 'fake@disposable.tk',
            'validator': email_validator.validate
        }
    ]
    
    for test in test_cases:
        result = test['validator'](test['value'])
        status = "✅" if result['is_valid'] else "⚠️"
        print(f"   {status} {test['type']}: {test['value'][:50]}...")
        
        if result.get('warnings'):
            for warning in result['warnings'][:2]:  # Show first 2 warnings
                print(f"      ⚠️  {warning}")
        
        if result.get('security_flags'):
            print(f"      🚨 Security flags: {', '.join(result['security_flags'])}")
    
    print("\n2. Resilience patterns...")
    
    print("   The system implements several resilience patterns:")
    print("   ✅ Rate limiting to prevent API abuse")
    print("   ✅ Retry logic with exponential backoff")
    print("   ✅ Circuit breaker for failing services")
    print("   ✅ Graceful degradation (SMTP fallback for SendGrid)")
    print("   ✅ Timeout handling for external calls")
    print("   ✅ Input validation and sanitization")
    print("   ✅ Caching to reduce external dependencies")
    
    print("\n3. Monitoring and alerting...")
    
    print("   Key monitoring points:")
    print("   📊 Email delivery success rates")
    print("   📊 WHOIS lookup performance")
    print("   📊 Search engine API availability")
    print("   📊 Response processing accuracy")
    print("   📊 Overall takedown success rates")
    
    print("\n   Alerting triggers:")
    print("   🚨 Success rate drops below 80%")
    print("   🚨 Email bounce rate exceeds 5%")
    print("   🚨 API rate limits exceeded")
    print("   🚨 Counter-notices received")
    print("   🚨 System errors or exceptions")


async def main():
    """Run all advanced feature examples."""
    
    print("🚀 AutoDMCA Advanced Features Demonstration")
    print("=" * 50)
    
    try:
        await response_handling_example()
        await anonymity_protection_example() 
        await template_customization_example()
        await performance_monitoring_example()
        await error_handling_example()
        
        print("\n🎉 Advanced features demonstration completed!")
        print("\nKey takeaways:")
        print("• AutoDMCA provides comprehensive anonymity protection")
        print("• Response handling supports all DMCA scenarios including counter-notices")
        print("• Templates are legally compliant with full validation")
        print("• Performance monitoring enables continuous optimization")
        print("• Robust error handling ensures system reliability")
        
    except Exception as e:
        print(f"\n❌ Advanced features demo failed: {str(e)}")
        raise


if __name__ == "__main__":
    """Run the advanced features example."""
    
    print("Starting AutoDMCA Advanced Features Example...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Example interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {str(e)}")
    
    print("\nFor more information, see the documentation at docs/")