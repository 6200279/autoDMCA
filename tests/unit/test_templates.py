"""
Unit tests for DMCA notice templates and rendering.

Tests template generation, validation, and rendering with proper
legal compliance and variable substitution.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.autodmca.templates.dmca_notice import DMCANoticeTemplate, DMCAFollowupTemplate, get_subject_line
from src.autodmca.templates.template_renderer import TemplateRenderer
from src.autodmca.models.takedown import TakedownRequest, CreatorProfile, InfringementData
from src.autodmca.models.hosting import DMCAAgent


class TestDMCANoticeTemplate:
    """Test cases for DMCA notice templates."""
    
    def test_get_standard_notice(self):
        """Test getting standard DMCA notice template."""
        template = DMCANoticeTemplate.get_standard_notice()
        
        assert isinstance(template, str)
        assert len(template) > 0
        assert "Digital Millennium Copyright Act" in template
        assert "{{ creator_name }}" in template
        assert "{{ infringing_url }}" in template
        assert "good faith belief" in template
        assert "penalty of perjury" in template
    
    def test_get_followup_notice(self):
        """Test getting follow-up notice template."""
        template = DMCANoticeTemplate.get_followup_notice()
        
        assert isinstance(template, str)
        assert len(template) > 0
        assert "follow-up" in template.lower()
        assert "{{ original_notice_date }}" in template
        assert "{{ followup_number }}" in template
    
    def test_get_final_notice(self):
        """Test getting final notice template."""
        template = DMCANoticeTemplate.get_final_notice()
        
        assert isinstance(template, str)
        assert len(template) > 0
        assert "final" in template.lower()
        assert "legal action" in template.lower()
        assert "{{ final_deadline_days }}" in template
    
    def test_get_search_delisting_template(self):
        """Test getting search delisting template."""
        template = DMCANoticeTemplate.get_search_delisting_template()
        
        assert isinstance(template, str)
        assert len(template) > 0
        assert "{{ creator_name }}" in template
        assert "{{ infringing_urls }}" in template
        assert "good faith belief" in template
    
    def test_validate_template_variables_complete(self):
        """Test template validation with all required variables."""
        template = "Hello {{ creator_name }}, your {{ original_work_title }} at {{ infringing_url }}"
        
        variables = {
            'creator_name': 'John Doe',
            'original_work_title': 'My Photo',
            'infringing_url': 'https://example.com/stolen.jpg'
        }
        
        errors = DMCANoticeTemplate.validate_template_variables(template, variables)
        assert len(errors) == 0
    
    def test_validate_template_variables_missing(self):
        """Test template validation with missing variables."""
        template = "Hello {{ creator_name }}, your work at {{ infringing_url }}"
        
        variables = {
            'creator_name': 'John Doe'
            # Missing infringing_url
        }
        
        errors = DMCANoticeTemplate.validate_template_variables(template, variables)
        assert len(errors) > 0
        assert 'infringing_url' in errors
    
    def test_validate_template_variables_invalid_email(self):
        """Test template validation with invalid email."""
        template = "Contact: {{ creator_email }}"
        
        variables = {
            'creator_email': 'invalid-email-format'
        }
        
        errors = DMCANoticeTemplate.validate_template_variables(template, variables)
        assert len(errors) > 0
        assert 'creator_email' in errors
        assert 'Invalid email format' in errors['creator_email']
    
    def test_validate_template_variables_invalid_url(self):
        """Test template validation with invalid URL."""
        template = "Infringing content: {{ infringing_url }}"
        
        variables = {
            'infringing_url': 'not-a-valid-url'
        }
        
        errors = DMCANoticeTemplate.validate_template_variables(template, variables)
        assert len(errors) > 0
        assert 'infringing_url' in errors
        assert 'Invalid URL format' in errors['infringing_url']
    
    def test_dmca_required_fields(self):
        """Test validation of DMCA-specific required fields."""
        template = "Generic template without DMCA fields"
        
        variables = {}  # Missing all required DMCA fields
        
        errors = DMCANoticeTemplate.validate_template_variables(template, variables)
        
        # Should flag missing required fields
        assert 'creator_name' in errors
        assert 'original_work_title' in errors
        assert 'infringing_url' in errors


class TestDMCAFollowupTemplate:
    """Test cases for DMCA follow-up templates."""
    
    def test_get_first_followup(self):
        """Test getting first follow-up template."""
        template = DMCAFollowupTemplate.get_first_followup()
        
        assert isinstance(template, str)
        assert len(template) > 0
        assert "follow-up" in template.lower()
    
    def test_get_second_followup(self):
        """Test getting second (more urgent) follow-up template."""
        template = DMCAFollowupTemplate.get_second_followup()
        
        assert isinstance(template, str)
        assert len(template) > 0
        assert "urgently" in template.lower()
        assert "will proceed" in template.lower()
    
    def test_get_final_notice(self):
        """Test getting final notice template."""
        template = DMCAFollowupTemplate.get_final_notice()
        
        assert isinstance(template, str)
        assert len(template) > 0
        assert "final" in template.lower()
    
    def test_get_escalation_warning(self):
        """Test getting escalation warning text."""
        warning = DMCAFollowupTemplate.get_escalation_warning()
        
        assert isinstance(warning, str)
        assert len(warning) > 0
        assert "legal counsel" in warning.lower()
        assert "litigation" in warning.lower()


class TestSubjectLines:
    """Test cases for email subject line generation."""
    
    def test_get_subject_line_initial(self):
        """Test initial notice subject line."""
        subject = get_subject_line('initial')
        
        assert subject == 'DMCA Takedown Notice - Copyright Infringement Claim'
    
    def test_get_subject_line_followup_with_title(self):
        """Test follow-up subject line with title."""
        subject = get_subject_line('followup_1', title='My Photo')
        
        assert 'My Photo' in subject
        assert 'DMCA Follow-up' in subject
    
    def test_get_subject_line_final(self):
        """Test final notice subject line."""
        subject = get_subject_line('final')
        
        assert 'FINAL NOTICE' in subject
        assert 'Legal Action Pending' in subject
    
    def test_get_subject_line_unknown_type(self):
        """Test unknown subject type falls back to initial."""
        subject = get_subject_line('unknown_type')
        
        assert subject == 'DMCA Takedown Notice - Copyright Infringement Claim'


class TestTemplateRenderer:
    """Test cases for template renderer."""
    
    @pytest.fixture
    def template_renderer(self):
        """Fixture for template renderer."""
        return TemplateRenderer()
    
    @pytest.fixture
    def sample_creator_profile(self):
        """Fixture for sample creator profile."""
        return CreatorProfile(
            public_name="Jane Creator",
            email="jane@example.com",
            address_line1="123 Creative Ave",
            city="Art City",
            state_province="CA",
            postal_code="90210",
            country="USA",
            protected_usernames=["janecreator"],
            platform_urls=["https://mysite.com/jane"],
            use_anonymity=True
        )
    
    @pytest.fixture
    def sample_infringement_data(self):
        """Fixture for sample infringement data."""
        return InfringementData(
            infringing_url="https://pirate-site.com/stolen-photo.jpg",
            description="Unauthorized use of my copyrighted photograph without permission",
            original_work_title="Beautiful Sunset Landscape",
            original_work_description="Original photograph taken during vacation in Hawaii",
            original_work_urls=["https://mysite.com/gallery/sunset.jpg"],
            content_type="image",
            creation_date=datetime(2023, 6, 15),
            publication_date=datetime(2023, 6, 20),
            detected_by="automated_scan",
            confidence_score=0.95
        )
    
    @pytest.fixture
    def sample_takedown_request(self, sample_creator_profile, sample_infringement_data):
        """Fixture for sample takedown request."""
        return TakedownRequest(
            creator_id=uuid4(),
            creator_profile=sample_creator_profile,
            infringement_data=sample_infringement_data,
            priority=7
        )
    
    @pytest.fixture
    def sample_dmca_agent(self):
        """Fixture for sample DMCA agent."""
        return DMCAAgent(
            name="Legal Services LLC",
            title="DMCA Agent",
            organization="Legal Services LLC",
            email="dmca@legalservices.com",
            phone="+1-555-123-4567",
            address_line1="456 Legal Avenue",
            city="Law City",
            state_province="NY",
            postal_code="10001",
            country="USA"
        )
    
    def test_render_dmca_notice_standard(
        self, 
        template_renderer, 
        sample_takedown_request, 
        sample_dmca_agent
    ):
        """Test rendering standard DMCA notice."""
        result = template_renderer.render_dmca_notice(
            sample_takedown_request,
            sample_dmca_agent,
            "standard"
        )
        
        assert 'subject' in result
        assert 'body' in result
        assert 'template_type' in result
        
        # Check that variables were substituted
        assert sample_takedown_request.creator_profile.public_name in result['body']
        assert str(sample_takedown_request.infringement_data.infringing_url) in result['body']
        assert sample_takedown_request.infringement_data.original_work_title in result['body']
        assert sample_dmca_agent.name in result['body']
        assert sample_dmca_agent.email in result['body']
        
        # Check for required DMCA elements
        assert "Digital Millennium Copyright Act" in result['body']
        assert "good faith belief" in result['body']
        assert "penalty of perjury" in result['body']
        assert "authorized to act" in result['body']
    
    def test_render_dmca_notice_followup(
        self, 
        template_renderer, 
        sample_takedown_request, 
        sample_dmca_agent
    ):
        """Test rendering follow-up DMCA notice."""
        # Set notice sent date for follow-up
        sample_takedown_request.notice_sent_at = datetime(2023, 7, 1)
        sample_takedown_request.followup_count = 1
        
        result = template_renderer.render_dmca_notice(
            sample_takedown_request,
            sample_dmca_agent,
            "followup"
        )
        
        assert result['template_type'] == 'followup'
        assert "follow-up" in result['body'].lower()
        assert "July 01, 2023" in result['body']  # Formatted date
    
    def test_render_dmca_notice_final(
        self, 
        template_renderer, 
        sample_takedown_request, 
        sample_dmca_agent
    ):
        """Test rendering final DMCA notice."""
        result = template_renderer.render_dmca_notice(
            sample_takedown_request,
            sample_dmca_agent,
            "final"
        )
        
        assert result['template_type'] == 'final'
        assert "final" in result['body'].lower()
        assert "legal action" in result['body'].lower()
    
    def test_render_without_agent(self, template_renderer, sample_takedown_request):
        """Test rendering DMCA notice without agent (non-anonymous)."""
        # Disable anonymity
        sample_takedown_request.creator_profile.use_anonymity = False
        
        result = template_renderer.render_dmca_notice(
            sample_takedown_request,
            None,  # No agent
            "standard"
        )
        
        # Should use creator's information directly
        assert sample_takedown_request.creator_profile.email in result['body']
        assert sample_takedown_request.creator_profile.public_name in result['body']
    
    def test_render_search_delisting_request(
        self, 
        template_renderer, 
        sample_takedown_request, 
        sample_dmca_agent
    ):
        """Test rendering search delisting request."""
        takedown_requests = [sample_takedown_request]
        
        result = template_renderer.render_search_delisting_request(
            takedown_requests,
            sample_dmca_agent
        )
        
        assert 'subject' in result
        assert 'body' in result
        assert 'template_type' in result
        assert result['template_type'] == 'search_delisting'
        assert result['url_count'] == 1
        
        # Check that URLs are included
        assert str(sample_takedown_request.infringement_data.infringing_url) in result['body']
        assert sample_dmca_agent.name in result['body']
    
    def test_render_search_delisting_multiple_urls(
        self, 
        template_renderer, 
        sample_takedown_request, 
        sample_dmca_agent
    ):
        """Test rendering search delisting request with multiple URLs."""
        # Create additional requests
        requests = [sample_takedown_request]
        
        for i in range(2):
            infringement = InfringementData(
                infringing_url=f"https://pirate-site.com/stolen{i}.jpg",
                description=f"Additional infringement {i}",
                original_work_title="Another Work",
                original_work_description="Another description",
                content_type="image"
            )
            
            request = TakedownRequest(
                creator_id=uuid4(),
                creator_profile=sample_takedown_request.creator_profile,
                infringement_data=infringement
            )
            requests.append(request)
        
        result = template_renderer.render_search_delisting_request(
            requests,
            sample_dmca_agent
        )
        
        assert result['url_count'] == 3
        # All URLs should be in the body
        for request in requests:
            assert str(request.infringement_data.infringing_url) in result['body']
    
    def test_prepare_template_variables(self, template_renderer, sample_takedown_request, sample_dmca_agent):
        """Test template variable preparation."""
        variables = template_renderer._prepare_template_variables(
            sample_takedown_request,
            sample_dmca_agent
        )
        
        # Check creator variables
        assert variables['creator_name'] == sample_takedown_request.creator_profile.public_name
        assert variables['creator_email'] == str(sample_takedown_request.creator_profile.email)
        
        # Check infringement variables
        assert variables['infringing_url'] == str(sample_takedown_request.infringement_data.infringing_url)
        assert variables['original_work_title'] == sample_takedown_request.infringement_data.original_work_title
        
        # Check agent variables
        assert variables['agent_contact'] == sample_dmca_agent
        assert variables['use_anonymity'] == sample_takedown_request.creator_profile.use_anonymity
        
        # Check date formatting
        assert variables['current_date'] is not None
        assert isinstance(variables['current_date'], str)
    
    def test_format_creator_address(self, template_renderer, sample_takedown_request):
        """Test creator address formatting."""
        address = template_renderer._format_creator_address(
            sample_takedown_request.creator_profile
        )
        
        lines = address.split('\n')
        assert sample_takedown_request.creator_profile.address_line1 in lines
        assert "Art City, CA 90210" in lines
        assert sample_takedown_request.creator_profile.country in lines
    
    def test_format_date(self, template_renderer):
        """Test date formatting."""
        test_date = datetime(2023, 7, 15, 14, 30)
        formatted = template_renderer._format_date(test_date)
        
        assert formatted == "July 15, 2023"
        
        # Test with None
        assert template_renderer._format_date(None) is None
    
    def test_sanitize_text(self, template_renderer):
        """Test text sanitization."""
        dangerous_text = '<script>alert("xss")</script>Hello <b>world</b>'
        sanitized = template_renderer._sanitize_text(dangerous_text)
        
        assert '<script>' not in sanitized
        assert '<b>' not in sanitized
        assert 'Hello world' in sanitized
    
    def test_truncate_url(self, template_renderer):
        """Test URL truncation."""
        long_url = "https://example.com/" + "a" * 200
        truncated = template_renderer._truncate_url(long_url, max_length=50)
        
        assert len(truncated) <= 50
        assert truncated.endswith("...")
        
        # Test short URL (no truncation)
        short_url = "https://example.com/short"
        not_truncated = template_renderer._truncate_url(short_url, max_length=50)
        
        assert not_truncated == short_url
    
    def test_validate_rendered_notice(self, template_renderer, sample_takedown_request, sample_dmca_agent):
        """Test validation of rendered notice."""
        rendered = template_renderer.render_dmca_notice(
            sample_takedown_request,
            sample_dmca_agent,
            "standard"
        )
        
        warnings = template_renderer.validate_rendered_notice(rendered)
        
        # Should have no warnings for a properly rendered notice
        assert len(warnings) == 0
    
    def test_validate_rendered_notice_incomplete(self, template_renderer):
        """Test validation of incomplete rendered notice."""
        incomplete_notice = {
            'subject': 'Test',
            'body': 'Short notice without required DMCA elements'
        }
        
        warnings = template_renderer.validate_rendered_notice(incomplete_notice)
        
        # Should have multiple warnings
        assert len(warnings) > 0
        assert any('Digital Millennium Copyright Act' in w for w in warnings)
        assert any('too short' in w for w in warnings)
    
    def test_template_with_missing_data(self, template_renderer):
        """Test template rendering with missing required data."""
        # Create minimal request with missing data
        minimal_creator = CreatorProfile(
            public_name="",  # Empty name should cause issues
            email="test@example.com",
            address_line1="123 Test St",
            city="Test City",
            state_province="CA",
            postal_code="12345",
            country="USA"
        )
        
        minimal_infringement = InfringementData(
            infringing_url="https://example.com/test",
            description="Test",
            original_work_title="",  # Empty title should cause issues
            original_work_description="Test",
            content_type="image"
        )
        
        minimal_request = TakedownRequest(
            creator_id=uuid4(),
            creator_profile=minimal_creator,
            infringement_data=minimal_infringement
        )
        
        # Should raise validation error
        with pytest.raises(ValueError):
            template_renderer.render_dmca_notice(minimal_request)