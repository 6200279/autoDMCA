"""
Unit tests for AutoDMCA services.

Tests the core services including WHOIS lookup, email dispatch,
search delisting, and DMCA orchestration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from src.autodmca.services.whois_service import WHOISService
from src.autodmca.services.email_service import EmailService
from src.autodmca.services.search_delisting_service import SearchDelistingService, SearchEngineType
from src.autodmca.services.dmca_service import DMCAService, DMCAServiceConfig
from src.autodmca.services.response_handler import ResponseHandler, ResponseType
from src.autodmca.models.takedown import TakedownRequest, TakedownStatus, CreatorProfile, InfringementData
from src.autodmca.models.hosting import HostingProvider, ContactInfo, DMCAAgent
from src.autodmca.utils.cache import CacheManager
from src.autodmca.utils.rate_limiter import RateLimiter


class TestWHOISService:
    """Test cases for WHOIS service."""
    
    @pytest.fixture
    def whois_service(self):
        """Fixture for WHOIS service."""
        cache_manager = CacheManager()
        rate_limiter = RateLimiter(max_calls=10, time_window=60)
        return WHOISService(cache_manager, rate_limiter, timeout=5)
    
    def test_extract_domain(self, whois_service):
        """Test domain extraction from URLs."""
        # Test various URL formats
        assert whois_service._extract_domain("https://example.com/path") == "example.com"
        assert whois_service._extract_domain("http://www.example.com") == "example.com"
        assert whois_service._extract_domain("https://subdomain.example.com:8080/path") == "subdomain.example.com"
        assert whois_service._extract_domain("example.com") == "example.com"
        
        # Test invalid URLs
        assert whois_service._extract_domain("invalid-url") is None
        assert whois_service._extract_domain("") is None
    
    def test_identify_provider(self, whois_service):
        """Test hosting provider identification."""
        # Test known provider identification
        registrar = "Amazon Technologies Inc."
        name_servers = ["ns1.amazonaws.com", "ns2.amazonaws.com"]
        domain = "example.com"
        
        provider_name = whois_service._identify_provider(registrar, name_servers, domain)
        assert "Amazon" in provider_name
        
        # Test fallback to registrar name
        unknown_registrar = "Unknown Registrar Corp"
        provider_name = whois_service._identify_provider(unknown_registrar, [], domain)
        assert "Unknown Registrar" in provider_name
    
    @pytest.mark.asyncio
    async def test_lookup_domain_cached(self, whois_service):
        """Test cached domain lookup."""
        # Mock cache hit
        cached_data = {
            'name': 'Test Provider',
            'domain': 'example.com',
            'registrar': 'Test Registrar'
        }
        
        with patch.object(whois_service.cache_manager, 'get', return_value=cached_data):
            result = await whois_service.lookup_domain("https://example.com/test")
            assert result.name == 'Test Provider'
            assert result.domain == 'example.com'
    
    @pytest.mark.asyncio
    async def test_lookup_domain_rate_limited(self, whois_service):
        """Test rate limiting in domain lookup."""
        with patch.object(whois_service.rate_limiter, 'acquire') as mock_acquire:
            mock_acquire.return_value = None
            
            with patch.object(whois_service.cache_manager, 'get', return_value=None):
                with patch.object(whois_service, '_perform_whois_lookup', return_value=None):
                    await whois_service.lookup_domain("https://example.com")
                    mock_acquire.assert_called_once()


class TestEmailService:
    """Test cases for email service."""
    
    @pytest.fixture
    def email_service(self):
        """Fixture for email service."""
        return EmailService(
            sendgrid_api_key="test_key",
            smtp_config={
                'host': 'smtp.test.com',
                'port': 587,
                'username': 'test@test.com',
                'password': 'password'
            }
        )
    
    @pytest.fixture
    def sample_takedown_request(self):
        """Fixture for sample takedown request."""
        creator_profile = CreatorProfile(
            public_name="Test Creator",
            email="creator@example.com",
            address_line1="123 Creator St",
            city="Creative City",
            state_province="CA",
            postal_code="12345",
            country="USA"
        )
        
        infringement_data = InfringementData(
            infringing_url="https://pirate.com/stolen.jpg",
            description="Unauthorized use of my photograph",
            original_work_title="Beautiful Landscape",
            original_work_description="Original photograph",
            content_type="image"
        )
        
        return TakedownRequest(
            creator_id=uuid4(),
            creator_profile=creator_profile,
            infringement_data=infringement_data
        )
    
    def test_validate_email(self, email_service):
        """Test email validation."""
        assert email_service._validate_email("test@example.com") is True
        assert email_service._validate_email("invalid-email") is False
        assert email_service._validate_email("") is False
        assert email_service._validate_email("test@") is False
    
    @pytest.mark.asyncio
    async def test_send_dmca_notice_validation(self, email_service, sample_takedown_request):
        """Test DMCA notice validation."""
        # Test with invalid email
        result = await email_service.send_dmca_notice(
            sample_takedown_request,
            "invalid-email",
            None
        )
        
        assert result['success'] is False
        assert "Invalid recipient email" in result['error']
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, email_service, sample_takedown_request):
        """Test email rate limiting."""
        with patch.object(email_service.rate_limiter, 'acquire') as mock_acquire:
            mock_acquire.return_value = None
            
            with patch.object(email_service, '_send_email', return_value={'success': True}):
                await email_service.send_dmca_notice(
                    sample_takedown_request,
                    "test@example.com",
                    None
                )
                mock_acquire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_batch_notices(self, email_service):
        """Test batch notice sending."""
        # Create multiple requests
        requests = []
        emails = []
        
        for i in range(3):
            creator_profile = CreatorProfile(
                public_name=f"Creator {i}",
                email=f"creator{i}@example.com",
                address_line1="123 Test St",
                city="Test City",
                state_province="CA",
                postal_code="12345",
                country="USA"
            )
            
            infringement_data = InfringementData(
                infringing_url=f"https://pirate.com/stolen{i}.jpg",
                description=f"Infringement {i}",
                original_work_title=f"Work {i}",
                original_work_description=f"Description {i}",
                content_type="image"
            )
            
            request = TakedownRequest(
                creator_id=uuid4(),
                creator_profile=creator_profile,
                infringement_data=infringement_data
            )
            
            requests.append(request)
            emails.append(f"host{i}@example.com")
        
        # Mock successful sends
        with patch.object(email_service, 'send_dmca_notice', return_value={'success': True}) as mock_send:
            result = await email_service.send_batch_notices(
                requests,
                emails,
                None,
                "standard",
                max_concurrent=2
            )
            
            assert result['total_sent'] == 3
            assert result['total_failed'] == 0
            assert mock_send.call_count == 3
    
    @pytest.mark.asyncio
    async def test_email_deliverability_validation(self, email_service):
        """Test email deliverability validation."""
        # Test valid email format
        result = await email_service.validate_email_deliverability("test@gmail.com")
        assert result['valid'] is True
        
        # Test invalid email format
        result = await email_service.validate_email_deliverability("invalid-email")
        assert result['valid'] is False
        assert result['deliverable'] is False


class TestSearchDelistingService:
    """Test cases for search delisting service."""
    
    @pytest.fixture
    def delisting_service(self):
        """Fixture for search delisting service."""
        return SearchDelistingService(
            google_api_key="test_google_key",
            google_custom_search_id="test_search_id",
            bing_api_key="test_bing_key"
        )
    
    @pytest.fixture
    def sample_takedown_requests(self):
        """Fixture for sample takedown requests."""
        creator_profile = CreatorProfile(
            public_name="Test Creator",
            email="creator@example.com",
            address_line1="123 Test St",
            city="Test City",
            state_province="CA",
            postal_code="12345",
            country="USA"
        )
        
        requests = []
        for i in range(2):
            infringement_data = InfringementData(
                infringing_url=f"https://pirate.com/stolen{i}.jpg",
                description=f"Infringement {i}",
                original_work_title=f"Work {i}",
                original_work_description=f"Description {i}",
                content_type="image"
            )
            
            request = TakedownRequest(
                creator_id=uuid4(),
                creator_profile=creator_profile,
                infringement_data=infringement_data
            )
            requests.append(request)
        
        return requests
    
    @pytest.mark.asyncio
    async def test_submit_delisting_request(self, delisting_service, sample_takedown_requests):
        """Test delisting request submission."""
        with patch.object(delisting_service, '_submit_batch_delisting') as mock_submit:
            mock_submit.return_value = {
                'submitted_count': 2,
                'failed_count': 0,
                'submission_id': 'test_123'
            }
            
            result = await delisting_service.submit_delisting_request(
                sample_takedown_requests,
                SearchEngineType.GOOGLE
            )
            
            assert result['success'] is True
            assert result['submitted_count'] == 2
            assert result['search_engine'] == SearchEngineType.GOOGLE
            mock_submit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_invalid_search_engine(self, delisting_service, sample_takedown_requests):
        """Test invalid search engine handling."""
        result = await delisting_service.submit_delisting_request(
            sample_takedown_requests,
            "invalid_engine"
        )
        
        assert result['success'] is False
        assert "Unsupported search engine" in result['error']
    
    @pytest.mark.asyncio
    async def test_empty_request_list(self, delisting_service):
        """Test empty request list handling."""
        result = await delisting_service.submit_delisting_request(
            [],
            SearchEngineType.GOOGLE
        )
        
        assert result['success'] is False
        assert "No takedown requests provided" in result['error']
    
    @pytest.mark.asyncio
    async def test_verify_delisting_status(self, delisting_service):
        """Test delisting verification."""
        urls = ["https://example.com/test1", "https://example.com/test2"]
        
        with patch.object(delisting_service, '_verify_google_delisting') as mock_verify:
            mock_verify.side_effect = [
                {'delisted': True, 'checked_at': datetime.utcnow().isoformat()},
                {'delisted': False, 'checked_at': datetime.utcnow().isoformat()}
            ]
            
            results = await delisting_service.verify_delisting_status(
                urls,
                SearchEngineType.GOOGLE
            )
            
            assert len(results) == 2
            assert results[urls[0]]['delisted'] is True
            assert results[urls[1]]['delisted'] is False
            assert mock_verify.call_count == 2


class TestDMCAService:
    """Test cases for main DMCA service."""
    
    @pytest.fixture
    def dmca_service(self):
        """Fixture for DMCA service."""
        # Mock services
        whois_service = MagicMock(spec=WHOISService)
        email_service = MagicMock(spec=EmailService)
        delisting_service = MagicMock(spec=SearchDelistingService)
        
        # DMCA agent
        agent = DMCAAgent(
            name="Test Agent",
            email="agent@legal.com",
            address_line1="456 Legal Ave",
            city="Law City",
            state_province="NY",
            postal_code="54321",
            country="USA"
        )
        
        config = DMCAServiceConfig(
            max_concurrent_requests=3,
            followup_interval_days=7,
            auto_search_delisting=True
        )
        
        return DMCAService(
            whois_service=whois_service,
            email_service=email_service,
            search_delisting_service=delisting_service,
            agent_contact=agent,
            config=config
        )
    
    @pytest.fixture
    def sample_takedown_request(self):
        """Fixture for sample takedown request."""
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
            infringing_url="https://pirate.com/stolen.jpg",
            description="Unauthorized use",
            original_work_title="My Work",
            original_work_description="Original work",
            content_type="image"
        )
        
        return TakedownRequest(
            creator_id=uuid4(),
            creator_profile=creator_profile,
            infringement_data=infringement_data
        )
    
    @pytest.mark.asyncio
    async def test_process_takedown_request_success(self, dmca_service, sample_takedown_request):
        """Test successful takedown request processing."""
        # Mock successful WHOIS lookup
        hosting_provider = HostingProvider(
            name="Test Hosting",
            domain="testhosting.com",
            abuse_email="abuse@testhosting.com"
        )
        dmca_service.whois_service.lookup_domain = AsyncMock(return_value=hosting_provider)
        
        # Mock successful email sending
        email_result = {
            'success': True,
            'message_id': 'test_message_123',
            'timestamp': datetime.utcnow().isoformat()
        }
        dmca_service.email_service.send_dmca_notice = AsyncMock(return_value=email_result)
        
        # Process request
        result = await dmca_service.process_takedown_request(sample_takedown_request)
        
        assert result['success'] is True
        assert result['hosting_provider'] == "Test Hosting"
        assert result['email_sent'] is True
        assert sample_takedown_request.status == TakedownStatus.UNDER_REVIEW
        assert sample_takedown_request.hosting_provider == "Test Hosting"
    
    @pytest.mark.asyncio
    async def test_process_takedown_request_whois_failure(self, dmca_service, sample_takedown_request):
        """Test takedown request with WHOIS lookup failure."""
        # Mock failed WHOIS lookup
        dmca_service.whois_service.lookup_domain = AsyncMock(return_value=None)
        
        result = await dmca_service.process_takedown_request(sample_takedown_request)
        
        assert result['success'] is False
        assert "WHOIS lookup failed" in result['message']
        assert sample_takedown_request.status == TakedownStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_process_takedown_request_email_failure(self, dmca_service, sample_takedown_request):
        """Test takedown request with email sending failure."""
        # Mock successful WHOIS lookup
        hosting_provider = HostingProvider(
            name="Test Hosting",
            domain="testhosting.com",
            abuse_email="abuse@testhosting.com"
        )
        dmca_service.whois_service.lookup_domain = AsyncMock(return_value=hosting_provider)
        
        # Mock failed email sending
        email_result = {
            'success': False,
            'error': 'Email sending failed'
        }
        dmca_service.email_service.send_dmca_notice = AsyncMock(return_value=email_result)
        
        result = await dmca_service.process_takedown_request(sample_takedown_request)
        
        assert result['success'] is False
        assert "Email sending failed" in result['message']
        assert sample_takedown_request.status == TakedownStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_send_followup(self, dmca_service, sample_takedown_request):
        """Test follow-up notice sending."""
        # Set up request for follow-up
        sample_takedown_request.notice_sent_at = datetime.utcnow() - timedelta(days=8)
        sample_takedown_request.abuse_email = "abuse@testhosting.com"
        
        # Mock successful follow-up sending
        followup_result = {
            'success': True,
            'message_id': 'followup_123'
        }
        dmca_service.email_service.send_followup_notice = AsyncMock(return_value=followup_result)
        
        result = await dmca_service.send_followup(sample_takedown_request)
        
        assert result['success'] is True
        assert sample_takedown_request.followup_count == 1
        assert sample_takedown_request.status == TakedownStatus.FOLLOWUP_REQUIRED
    
    @pytest.mark.asyncio
    async def test_send_followup_max_attempts(self, dmca_service, sample_takedown_request):
        """Test follow-up with maximum attempts reached."""
        # Set follow-up count to maximum
        sample_takedown_request.followup_count = 3
        
        result = await dmca_service.send_followup(sample_takedown_request)
        
        assert result['success'] is False
        assert "Maximum follow-up attempts reached" in result['message']
    
    @pytest.mark.asyncio
    async def test_request_search_delisting(self, dmca_service, sample_takedown_request):
        """Test search engine delisting request."""
        delisting_result = {
            'success': True,
            'submitted_count': 1,
            'search_engine': SearchEngineType.GOOGLE
        }
        
        dmca_service.search_delisting_service.submit_delisting_request = AsyncMock(
            return_value=delisting_result
        )
        
        result = await dmca_service.request_search_delisting([sample_takedown_request])
        
        assert result['success'] is True
        assert SearchEngineType.GOOGLE in result['results']
        assert sample_takedown_request.status == TakedownStatus.SEARCH_DELISTING_REQUESTED
    
    @pytest.mark.asyncio
    async def test_check_takedown_status(self, dmca_service, sample_takedown_request):
        """Test takedown status checking."""
        # Set up request with some history
        sample_takedown_request.notice_sent_at = datetime.utcnow() - timedelta(days=3)
        sample_takedown_request.followup_count = 1
        
        result = await dmca_service.check_takedown_status(sample_takedown_request)
        
        assert result['request_id'] == str(sample_takedown_request.id)
        assert result['current_status'] == sample_takedown_request.status.value
        assert result['followup_count'] == 1
        assert result['email_sent'] is True
        assert 'next_action' in result


class TestResponseHandler:
    """Test cases for response handler service."""
    
    @pytest.fixture
    def response_handler(self):
        """Fixture for response handler."""
        email_service = MagicMock(spec=EmailService)
        return ResponseHandler(email_service)
    
    def test_classify_response_acknowledgment(self, response_handler):
        """Test response classification for acknowledgments."""
        email_content = "Thank you for your DMCA notice. We have received your complaint and assigned reference number 12345."
        subject = "Re: DMCA Notice Received"
        
        classification = response_handler._classify_response(email_content, subject)
        
        assert classification['type'] == ResponseType.ACKNOWLEDGMENT
        assert classification['confidence'] > 0.5
        assert len(classification['indicators']) > 0
    
    def test_classify_response_takedown_complete(self, response_handler):
        """Test response classification for completed takedowns."""
        email_content = "The content has been successfully removed from our platform as requested."
        subject = "Content Removed - DMCA Compliance"
        
        classification = response_handler._classify_response(email_content, subject)
        
        assert classification['type'] == ResponseType.TAKEDOWN_COMPLETE
        assert classification['confidence'] > 0.5
    
    def test_classify_response_counter_notice(self, response_handler):
        """Test response classification for counter-notices."""
        email_content = """
        This is a counter-notice pursuant to Section 512(g) of the DMCA.
        I have a good faith belief that the material was removed by mistake.
        """
        subject = "Counter-Notice for DMCA Takedown"
        
        classification = response_handler._classify_response(email_content, subject)
        
        assert classification['type'] == ResponseType.COUNTER_NOTICE
        assert classification['counter_notice'] is True
        assert classification['confidence'] > 0.7
    
    def test_classify_response_rejection(self, response_handler):
        """Test response classification for rejections."""
        email_content = "We cannot remove the content as it appears to be fair use under copyright law."
        subject = "DMCA Request Rejected"
        
        classification = response_handler._classify_response(email_content, subject)
        
        assert classification['type'] == ResponseType.REJECTION
        assert classification['confidence'] > 0.5
    
    def test_classify_response_auto_reply(self, response_handler):
        """Test response classification for auto-replies."""
        email_content = "This is an automatic response. I am currently out of office."
        subject = "Auto-Reply: Your Message"
        
        classification = response_handler._classify_response(email_content, subject)
        
        assert classification['type'] == ResponseType.AUTO_REPLY
        assert classification['confidence'] > 0.5
    
    def test_parse_counter_notice(self, response_handler):
        """Test counter-notice parsing."""
        counter_notice_content = """
        I have a good faith belief that the material was removed or disabled as a result of mistake.
        I consent to the jurisdiction of Federal District Court.
        I swear, under penalty of perjury, that the above information is accurate.
        
        Contact Information:
        John Doe
        john.doe@example.com
        (555) 123-4567
        123 Main St, Anytown, CA 12345
        """
        
        parsed = response_handler._parse_counter_notice(counter_notice_content)
        
        assert parsed['good_faith_statement'] is True
        assert parsed['penalty_statement'] is True
        assert parsed['jurisdiction_consent'] is True
        assert parsed['subscriber_info']['email'] == 'john.doe@example.com'
        assert parsed['has_required_elements'] is True
    
    def test_parse_incomplete_counter_notice(self, response_handler):
        """Test parsing of incomplete counter-notice."""
        incomplete_content = "This content should not have been removed."
        
        parsed = response_handler._parse_counter_notice(incomplete_content)
        
        assert parsed['has_required_elements'] is False
        assert parsed['good_faith_statement'] is False
        assert parsed['penalty_statement'] is False
    
    @pytest.mark.asyncio
    async def test_process_email_response_no_match(self, response_handler):
        """Test processing email response with no matching takedown request."""
        with patch.object(response_handler, '_find_related_takedown_request', return_value=None):
            result = await response_handler.process_email_response(
                "Test email content",
                "sender@example.com",
                "Test Subject"
            )
            
            assert result['success'] is False
            assert "No matching takedown request found" in result['reason']
    
    @pytest.mark.asyncio
    async def test_store_response_data(self, response_handler):
        """Test response data storage."""
        request_id = uuid4()
        classification = {
            'type': ResponseType.ACKNOWLEDGMENT,
            'confidence': 0.8,
            'indicators': ['test indicator']
        }
        
        with patch.object(response_handler.cache_manager, 'set') as mock_set:
            await response_handler._store_response_data(
                request_id,
                classification,
                "Email content",
                "sender@example.com",
                "Subject",
                "msg_123"
            )
            
            mock_set.assert_called_once()
            # Verify the stored data structure
            stored_data = mock_set.call_args[0][1]
            assert stored_data['request_id'] == str(request_id)
            assert stored_data['classification'] == classification