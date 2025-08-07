"""
Unit tests for AutoDMCA models.

Tests the core data models including TakedownRequest, CreatorProfile,
InfringementData, and HostingProvider with comprehensive validation.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.autodmca.models.takedown import (
    TakedownRequest, 
    TakedownStatus, 
    CreatorProfile, 
    InfringementData,
    TakedownBatch
)
from src.autodmca.models.hosting import (
    HostingProvider, 
    ContactInfo, 
    DMCAAgent
)


class TestCreatorProfile:
    """Test cases for CreatorProfile model."""
    
    def test_valid_creator_profile(self):
        """Test creating a valid creator profile."""
        profile = CreatorProfile(
            public_name="Jane Creator",
            email="jane@example.com",
            address_line1="123 Main St",
            city="Los Angeles",
            state_province="CA",
            postal_code="90210",
            country="USA",
            protected_usernames=["janecreator", "jane_official"],
            platform_urls=["https://example.com/jane"],
            use_anonymity=True,
            agent_representation=True
        )
        
        assert profile.public_name == "Jane Creator"
        assert profile.email == "jane@example.com"
        assert profile.use_anonymity is True
        assert len(profile.protected_usernames) == 2
    
    def test_invalid_email(self):
        """Test that invalid email raises validation error."""
        with pytest.raises(ValueError):
            CreatorProfile(
                public_name="Jane Creator",
                email="invalid-email",  # Invalid email format
                address_line1="123 Main St",
                city="Los Angeles",
                state_province="CA",
                postal_code="90210",
                country="USA"
            )
    
    def test_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValueError):
            CreatorProfile(
                public_name="",  # Required field empty
                email="jane@example.com",
                address_line1="123 Main St",
                city="Los Angeles",
                state_province="CA",
                postal_code="90210",
                country="USA"
            )
    
    def test_phone_validation(self):
        """Test phone number validation."""
        # Valid phone number
        profile = CreatorProfile(
            public_name="Jane Creator",
            email="jane@example.com",
            phone="+1-555-123-4567",
            address_line1="123 Main St",
            city="Los Angeles",
            state_province="CA",
            postal_code="90210",
            country="USA"
        )
        assert profile.phone == "+1-555-123-4567"
        
        # Invalid phone number
        with pytest.raises(ValueError):
            CreatorProfile(
                public_name="Jane Creator",
                email="jane@example.com",
                phone="invalid-phone",
                address_line1="123 Main St",
                city="Los Angeles",
                state_province="CA",
                postal_code="90210",
                country="USA"
            )


class TestInfringementData:
    """Test cases for InfringementData model."""
    
    def test_valid_infringement_data(self):
        """Test creating valid infringement data."""
        infringement = InfringementData(
            infringing_url="https://pirate-site.com/stolen-content.jpg",
            description="Unauthorized use of my copyrighted photograph",
            original_work_title="Beautiful Sunset Photo",
            original_work_description="Original photograph taken on vacation",
            original_work_urls=["https://my-site.com/gallery/sunset.jpg"],
            content_type="image",
            creation_date=datetime(2023, 6, 15),
            detected_by="automated_scan",
            confidence_score=0.95
        )
        
        assert str(infringement.infringing_url) == "https://pirate-site.com/stolen-content.jpg"
        assert infringement.content_type == "image"
        assert infringement.confidence_score == 0.95
    
    def test_invalid_url(self):
        """Test that invalid URLs raise validation errors."""
        with pytest.raises(ValueError):
            InfringementData(
                infringing_url="not-a-valid-url",
                description="Test description",
                original_work_title="Test Work",
                original_work_description="Test work description",
                content_type="image"
            )
    
    def test_content_type_validation(self):
        """Test content type validation."""
        # Valid content type
        infringement = InfringementData(
            infringing_url="https://example.com/test.jpg",
            description="Test description",
            original_work_title="Test Work",
            original_work_description="Test work description",
            content_type="video"
        )
        assert infringement.content_type == "video"
        
        # Invalid content type
        with pytest.raises(ValueError):
            InfringementData(
                infringing_url="https://example.com/test.jpg",
                description="Test description",
                original_work_title="Test Work",
                original_work_description="Test work description",
                content_type="invalid-type"
            )
    
    def test_confidence_score_validation(self):
        """Test confidence score validation."""
        # Valid confidence score
        infringement = InfringementData(
            infringing_url="https://example.com/test.jpg",
            description="Test description",
            original_work_title="Test Work",
            original_work_description="Test work description",
            content_type="image",
            confidence_score=0.75
        )
        assert infringement.confidence_score == 0.75
        
        # Invalid confidence score (too high)
        with pytest.raises(ValueError):
            InfringementData(
                infringing_url="https://example.com/test.jpg",
                description="Test description",
                original_work_title="Test Work",
                original_work_description="Test work description",
                content_type="image",
                confidence_score=1.5
            )
        
        # Invalid confidence score (negative)
        with pytest.raises(ValueError):
            InfringementData(
                infringing_url="https://example.com/test.jpg",
                description="Test description",
                original_work_title="Test Work",
                original_work_description="Test work description",
                content_type="image",
                confidence_score=-0.1
            )


class TestTakedownRequest:
    """Test cases for TakedownRequest model."""
    
    @pytest.fixture
    def valid_creator_profile(self):
        """Fixture for valid creator profile."""
        return CreatorProfile(
            public_name="Test Creator",
            email="test@example.com",
            address_line1="123 Test St",
            city="Test City",
            state_province="CA",
            postal_code="12345",
            country="USA"
        )
    
    @pytest.fixture
    def valid_infringement_data(self):
        """Fixture for valid infringement data."""
        return InfringementData(
            infringing_url="https://pirate-site.com/stolen.jpg",
            description="Unauthorized use of my content",
            original_work_title="My Original Work",
            original_work_description="Original creative work",
            content_type="image"
        )
    
    def test_valid_takedown_request(self, valid_creator_profile, valid_infringement_data):
        """Test creating a valid takedown request."""
        request = TakedownRequest(
            creator_id=uuid4(),
            creator_profile=valid_creator_profile,
            infringement_data=valid_infringement_data,
            priority=7
        )
        
        assert request.status == TakedownStatus.PENDING
        assert request.priority == 7
        assert request.followup_count == 0
        assert request.content_removed is False
        assert isinstance(request.id, type(uuid4()))
    
    def test_update_status(self, valid_creator_profile, valid_infringement_data):
        """Test status update functionality."""
        request = TakedownRequest(
            creator_id=uuid4(),
            creator_profile=valid_creator_profile,
            infringement_data=valid_infringement_data
        )
        
        original_time = request.updated_at
        
        # Update status
        request.update_status(TakedownStatus.NOTICE_SENT, {"test": "metadata"})
        
        assert request.status == TakedownStatus.NOTICE_SENT
        assert request.updated_at > original_time
        assert request.notice_sent_at is not None
        assert request.metadata["test"] == "metadata"
    
    def test_should_followup(self, valid_creator_profile, valid_infringement_data):
        """Test follow-up logic."""
        request = TakedownRequest(
            creator_id=uuid4(),
            creator_profile=valid_creator_profile,
            infringement_data=valid_infringement_data
        )
        
        # Should not follow up initially
        assert request.should_followup() is False
        
        # Set notice sent time to 8 days ago
        request.notice_sent_at = datetime.utcnow() - timedelta(days=8)
        
        # Should follow up now
        assert request.should_followup(followup_interval_days=7) is True
        
        # Set max follow-ups reached
        request.followup_count = 3
        
        # Should not follow up when max reached
        assert request.should_followup(max_followups=3) is False
    
    def test_is_expired(self, valid_creator_profile, valid_infringement_data):
        """Test expiration logic."""
        request = TakedownRequest(
            creator_id=uuid4(),
            creator_profile=valid_creator_profile,
            infringement_data=valid_infringement_data
        )
        
        # Should not be expired initially
        assert request.is_expired() is False
        
        # Set creation time to 35 days ago
        request.created_at = datetime.utcnow() - timedelta(days=35)
        
        # Should be expired with 30-day limit
        assert request.is_expired(max_age_days=30) is True
        
        # Should not be expired if completed
        request.update_status(TakedownStatus.COMPLETED)
        assert request.is_expired(max_age_days=30) is False
    
    def test_get_next_action(self, valid_creator_profile, valid_infringement_data):
        """Test next action recommendations."""
        request = TakedownRequest(
            creator_id=uuid4(),
            creator_profile=valid_creator_profile,
            infringement_data=valid_infringement_data
        )
        
        # Should recommend WHOIS lookup for pending status
        assert "WHOIS lookup" in request.get_next_action()
        
        # Change status and check recommendation
        request.update_status(TakedownStatus.NOTICE_GENERATED)
        assert "Send DMCA notice" in request.get_next_action()
    
    def test_priority_validation(self, valid_creator_profile, valid_infringement_data):
        """Test priority validation."""
        # Valid priority
        request = TakedownRequest(
            creator_id=uuid4(),
            creator_profile=valid_creator_profile,
            infringement_data=valid_infringement_data,
            priority=8
        )
        assert request.priority == 8
        
        # Invalid priority (too high)
        with pytest.raises(ValueError):
            TakedownRequest(
                creator_id=uuid4(),
                creator_profile=valid_creator_profile,
                infringement_data=valid_infringement_data,
                priority=15
            )
        
        # Invalid priority (too low)
        with pytest.raises(ValueError):
            TakedownRequest(
                creator_id=uuid4(),
                creator_profile=valid_creator_profile,
                infringement_data=valid_infringement_data,
                priority=0
            )


class TestTakedownBatch:
    """Test cases for TakedownBatch model."""
    
    @pytest.fixture
    def sample_requests(self):
        """Fixture for sample takedown requests."""
        creator_profile = CreatorProfile(
            public_name="Test Creator",
            email="test@example.com",
            address_line1="123 Test St",
            city="Test City",
            state_province="CA",
            postal_code="12345",
            country="USA"
        )
        
        requests = []
        for i in range(3):
            infringement = InfringementData(
                infringing_url=f"https://pirate-site.com/stolen{i}.jpg",
                description=f"Unauthorized use of content {i}",
                original_work_title=f"Original Work {i}",
                original_work_description=f"Description {i}",
                content_type="image"
            )
            
            request = TakedownRequest(
                creator_id=uuid4(),
                creator_profile=creator_profile,
                infringement_data=infringement
            )
            requests.append(request)
        
        return requests
    
    def test_valid_batch(self, sample_requests):
        """Test creating a valid takedown batch."""
        batch = TakedownBatch(
            creator_id=uuid4(),
            requests=sample_requests,
            priority=6
        )
        
        assert len(batch.requests) == 3
        assert batch.priority == 6
        assert isinstance(batch.batch_id, type(uuid4()))
    
    def test_batch_size_validation(self, sample_requests):
        """Test batch size validation."""
        # Valid batch (within limits)
        batch = TakedownBatch(
            creator_id=uuid4(),
            requests=sample_requests[:1],  # Single request
            priority=5
        )
        assert len(batch.requests) == 1
        
        # Empty batch should fail
        with pytest.raises(ValueError):
            TakedownBatch(
                creator_id=uuid4(),
                requests=[],  # Empty list
                priority=5
            )
    
    def test_status_summary(self, sample_requests):
        """Test batch status summary."""
        # Set different statuses
        sample_requests[0].update_status(TakedownStatus.COMPLETED)
        sample_requests[1].update_status(TakedownStatus.NOTICE_SENT)
        sample_requests[2].update_status(TakedownStatus.FAILED)
        
        batch = TakedownBatch(
            creator_id=uuid4(),
            requests=sample_requests
        )
        
        summary = batch.get_status_summary()
        assert summary[TakedownStatus.COMPLETED] == 1
        assert summary[TakedownStatus.NOTICE_SENT] == 1
        assert summary[TakedownStatus.FAILED] == 1
    
    def test_is_complete(self, sample_requests):
        """Test batch completion check."""
        batch = TakedownBatch(
            creator_id=uuid4(),
            requests=sample_requests
        )
        
        # Should not be complete initially
        assert batch.is_complete is False
        
        # Mark all as completed
        for request in sample_requests:
            request.update_status(TakedownStatus.COMPLETED)
        
        # Should be complete now
        assert batch.is_complete is True
        
        # Mark one as failed - should still be complete
        sample_requests[0].update_status(TakedownStatus.FAILED)
        assert batch.is_complete is True
    
    def test_completion_rate(self, sample_requests):
        """Test completion rate calculation."""
        batch = TakedownBatch(
            creator_id=uuid4(),
            requests=sample_requests
        )
        
        # Initially 0% completion
        assert batch.completion_rate == 0.0
        
        # Complete one request (33.33%)
        sample_requests[0].update_status(TakedownStatus.COMPLETED)
        expected_rate = (1 / 3) * 100
        assert abs(batch.completion_rate - expected_rate) < 0.01
        
        # Complete all requests (100%)
        for request in sample_requests:
            request.update_status(TakedownStatus.COMPLETED)
        
        assert batch.completion_rate == 100.0


class TestContactInfo:
    """Test cases for ContactInfo model."""
    
    def test_valid_contact_info(self):
        """Test creating valid contact information."""
        contact = ContactInfo(
            name="John Doe",
            email="john@example.com",
            phone="+1-555-123-4567",
            address_line1="123 Main St",
            city="Anytown",
            state_province="CA",
            postal_code="12345",
            country="USA"
        )
        
        assert contact.name == "John Doe"
        assert contact.email == "john@example.com"
        assert contact.is_complete() is True
    
    def test_is_complete(self):
        """Test completeness validation."""
        # Complete contact
        complete_contact = ContactInfo(
            name="John Doe",
            email="john@example.com"
        )
        assert complete_contact.is_complete() is True
        
        # Incomplete contact (no email)
        incomplete_contact = ContactInfo(
            name="John Doe"
        )
        assert incomplete_contact.is_complete() is False
        
        # Complete with contact form URL instead of email
        form_contact = ContactInfo(
            name="John Doe",
            contact_form_url="https://example.com/contact"
        )
        assert form_contact.is_complete() is True
    
    def test_get_display_address(self):
        """Test address formatting."""
        contact = ContactInfo(
            name="John Doe",
            address_line1="123 Main St",
            address_line2="Apt 4B",
            city="Anytown",
            state_province="CA",
            postal_code="12345",
            country="USA"
        )
        
        address = contact.get_display_address()
        assert "123 Main St" in address
        assert "Apt 4B" in address
        assert "Anytown, CA 12345" in address
        assert "USA" in address


class TestDMCAAgent:
    """Test cases for DMCAAgent model."""
    
    def test_valid_dmca_agent(self):
        """Test creating a valid DMCA agent."""
        agent = DMCAAgent(
            name="Legal Services Inc",
            email="dmca@legalservices.com",
            address_line1="456 Legal Ave",
            city="Law City",
            state_province="NY",
            postal_code="54321",
            country="USA",
            organization="Legal Services Inc"
        )
        
        assert agent.name == "Legal Services Inc"
        assert agent.title == "DMCA Agent"  # Default value
        assert agent.organization == "Legal Services Inc"
    
    def test_get_signature_block(self):
        """Test signature block generation."""
        agent = DMCAAgent(
            name="Jane Legal",
            title="Legal Counsel",
            organization="Law Firm LLC",
            email="jane@lawfirm.com",
            phone="+1-555-987-6543",
            address_line1="789 Court St",
            city="Legal Town",
            state_province="TX",
            postal_code="78901",
            country="USA",
            bar_number="TX123456",
            jurisdiction="Texas"
        )
        
        signature = agent.get_signature_block()
        assert "Jane Legal" in signature
        assert "Legal Counsel" in signature
        assert "Law Firm LLC" in signature
        assert "jane@lawfirm.com" in signature
        assert "+1-555-987-6543" in signature
        assert "Bar No: TX123456 (Texas)" in signature
    
    def test_get_formatted_address(self):
        """Test address formatting."""
        agent = DMCAAgent(
            name="Test Agent",
            email="test@example.com",
            address_line1="123 Test St",
            address_line2="Suite 100",
            city="Test City",
            state_province="CA",
            postal_code="12345",
            country="USA"
        )
        
        address = agent.get_formatted_address()
        lines = address.split('\n')
        assert "123 Test St" in lines
        assert "Suite 100" in lines
        assert "Test City, CA 12345" in lines
        assert "USA" in lines


class TestHostingProvider:
    """Test cases for HostingProvider model."""
    
    def test_valid_hosting_provider(self):
        """Test creating a valid hosting provider."""
        contact = ContactInfo(
            name="Support Team",
            email="support@hosting.com"
        )
        
        provider = HostingProvider(
            name="Test Hosting",
            domain="hosting.com",
            abuse_email="abuse@hosting.com",
            dmca_email="dmca@hosting.com",
            technical_contact=contact
        )
        
        assert provider.name == "Test Hosting"
        assert provider.domain == "hosting.com"
        assert provider.success_rate == 0.0  # No attempts yet
        assert provider.primary_contact_email == "dmca@hosting.com"
    
    def test_update_performance(self):
        """Test performance metrics update."""
        provider = HostingProvider(
            name="Test Hosting",
            domain="hosting.com"
        )
        
        # Initially no metrics
        assert provider.success_rate == 0.0
        assert provider.total_notices_sent == 0
        
        # Record successful takedown
        provider.update_performance(success=True, response_days=3)
        
        assert provider.total_notices_sent == 1
        assert provider.successful_takedowns == 1
        assert provider.success_rate == 100.0
        assert provider.average_response_days == 3
        
        # Record failed takedown
        provider.update_performance(success=False, response_days=7)
        
        assert provider.total_notices_sent == 2
        assert provider.successful_takedowns == 1
        assert provider.failed_attempts == 1
        assert provider.success_rate == 50.0
        assert provider.average_response_days == 5  # Average of 3 and 7
    
    def test_is_reliable(self):
        """Test reliability assessment."""
        provider = HostingProvider(
            name="Test Hosting",
            domain="hosting.com",
            is_dmca_compliant=True
        )
        
        # Should be reliable with benefit of doubt (few notices)
        assert provider.is_reliable() is True
        
        # Add some performance data
        for _ in range(6):
            provider.update_performance(success=True, response_days=2)
        
        # Should still be reliable with good performance
        assert provider.is_reliable() is True
        
        # Add failed attempts to lower success rate
        for _ in range(10):
            provider.update_performance(success=False, response_days=30)
        
        # Should not be reliable with poor performance
        assert provider.is_reliable() is False
    
    def test_get_best_contact(self):
        """Test best contact selection."""
        dmca_agent = ContactInfo(
            name="DMCA Agent",
            email="dmca@hosting.com"
        )
        
        tech_contact = ContactInfo(
            name="Tech Support",
            email="tech@hosting.com"
        )
        
        provider = HostingProvider(
            name="Test Hosting",
            domain="hosting.com",
            dmca_agent_info=dmca_agent,
            technical_contact=tech_contact
        )
        
        # Should prefer DMCA agent
        best_contact = provider.get_best_contact()
        assert best_contact == dmca_agent
        
        # Remove DMCA agent
        provider.dmca_agent_info = None
        
        # Should fall back to technical contact
        best_contact = provider.get_best_contact()
        assert best_contact == tech_contact