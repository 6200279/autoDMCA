"""
Comprehensive tests for DMCA takedown services including notice generation,
hosting provider integration, and takedown tracking.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import json
from typing import Dict, Any, List

from app.services.dmca.takedown_processor import TakedownProcessor, TakedownStatus
from app.services.dmca.integration import DMCAServiceIntegration, HostingProvider
from app.services.notifications.alert_system import AlertSystem
from app.schemas.takedown import TakedownCreate, TakedownResponse


@pytest.mark.unit
@pytest.mark.dmca
class TestTakedownProcessor:
    """Test DMCA takedown processing functionality."""

    @pytest.fixture
    def takedown_processor(self):
        """Create takedown processor instance."""
        return TakedownProcessor()

    @pytest.fixture
    def sample_takedown_request(self):
        """Create sample takedown request."""
        return TakedownCreate(
            profile_id=1,
            infringing_url="https://piracy-site.com/stolen-content",
            original_work_title="My Original Content",
            copyright_owner="Test Creator",
            contact_email="creator@example.com",
            infringement_description="My copyrighted content was stolen and posted without permission",
            good_faith_statement=True,
            accuracy_statement=True,
            signature="Test Creator",
            evidence_urls=["https://original-site.com/proof"],
            additional_information="This content was originally published on my OnlyFans account"
        )

    @pytest.fixture
    def mock_hosting_provider_data(self):
        """Mock hosting provider data."""
        return {
            "domain": "piracy-site.com",
            "dmca_email": "dmca@piracy-site.com",
            "response_time": "3-5 business days",
            "success_rate": 0.85,
            "provider_type": "hosting",
            "contact_info": {
                "email": "dmca@piracy-site.com",
                "phone": "+1-555-DMCA",
                "address": "123 Hosting St, Web City, WC 12345"
            }
        }

    @pytest.mark.asyncio
    async def test_process_takedown_request_success(self, takedown_processor, sample_takedown_request):
        """Test successful takedown request processing."""
        with patch.object(takedown_processor, '_generate_dmca_notice') as mock_generate:
            mock_generate.return_value = {
                "html_content": "<html>DMCA Notice</html>",
                "text_content": "DMCA Notice Text",
                "notice_id": "notice_123"
            }
            
            with patch.object(takedown_processor, '_send_takedown_notice') as mock_send:
                mock_send.return_value = {
                    "success": True,
                    "message_id": "msg_123",
                    "provider_response": "Notice received"
                }
                
                result = await takedown_processor.process_takedown(sample_takedown_request)
                
                assert result is not None
                assert result["status"] == "submitted"
                assert "notice_id" in result
                assert "message_id" in result

    @pytest.mark.asyncio
    async def test_generate_dmca_notice_content(self, takedown_processor, sample_takedown_request):
        """Test DMCA notice content generation."""
        notice = await takedown_processor._generate_dmca_notice(sample_takedown_request)
        
        assert notice is not None
        assert "html_content" in notice
        assert "text_content" in notice
        
        # Check required DMCA elements are present
        html_content = notice["html_content"]
        assert sample_takedown_request.copyright_owner in html_content
        assert sample_takedown_request.infringing_url in html_content
        assert sample_takedown_request.contact_email in html_content
        assert "good faith belief" in html_content.lower()

    @pytest.mark.asyncio
    async def test_identify_hosting_provider(self, takedown_processor, mock_hosting_provider_data):
        """Test hosting provider identification."""
        url = "https://piracy-site.com/stolen-content"
        
        with patch.object(takedown_processor, '_lookup_hosting_provider') as mock_lookup:
            mock_lookup.return_value = mock_hosting_provider_data
            
            provider = await takedown_processor._identify_hosting_provider(url)
            
            assert provider is not None
            assert provider["domain"] == "piracy-site.com"
            assert provider["dmca_email"] == "dmca@piracy-site.com"

    @pytest.mark.asyncio
    async def test_send_takedown_notice_success(self, takedown_processor):
        """Test successful takedown notice sending."""
        notice_data = {
            "html_content": "<html>Notice</html>",
            "text_content": "Notice text",
            "recipient": "dmca@provider.com"
        }
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = await takedown_processor._send_takedown_notice(notice_data)
            
            assert result["success"] is True
            assert "message_id" in result
            mock_server.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_takedown_notice_failure(self, takedown_processor):
        """Test takedown notice sending failure."""
        notice_data = {
            "html_content": "<html>Notice</html>",
            "text_content": "Notice text",
            "recipient": "invalid@email"
        }
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP Error")
            
            result = await takedown_processor._send_takedown_notice(notice_data)
            
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_track_takedown_status(self, takedown_processor):
        """Test takedown status tracking."""
        takedown_id = "td_123"
        
        with patch.object(takedown_processor, '_get_takedown_status') as mock_status:
            mock_status.return_value = {
                "id": takedown_id,
                "status": "pending",
                "sent_at": datetime.utcnow(),
                "provider_response": None
            }
            
            status = await takedown_processor.get_takedown_status(takedown_id)
            
            assert status["id"] == takedown_id
            assert status["status"] == "pending"

    @pytest.mark.asyncio
    async def test_update_takedown_response(self, takedown_processor):
        """Test updating takedown with provider response."""
        takedown_id = "td_123"
        response_data = {
            "status": "successful",
            "content_removed": True,
            "provider_message": "Content has been removed",
            "response_time": "2 days"
        }
        
        with patch.object(takedown_processor, '_update_takedown_record') as mock_update:
            mock_update.return_value = True
            
            result = await takedown_processor.update_takedown_response(
                takedown_id, 
                response_data
            )
            
            assert result is True
            mock_update.assert_called_once_with(takedown_id, response_data)

    @pytest.mark.asyncio
    async def test_batch_process_takedowns(self, takedown_processor, sample_takedown_request):
        """Test batch processing of multiple takedown requests."""
        requests = [sample_takedown_request for _ in range(5)]
        
        with patch.object(takedown_processor, 'process_takedown') as mock_process:
            mock_process.return_value = {
                "status": "submitted",
                "notice_id": "notice_123"
            }
            
            results = await takedown_processor.batch_process_takedowns(requests)
            
            assert len(results) == 5
            assert all(r["status"] == "submitted" for r in results)
            assert mock_process.call_count == 5

    def test_validate_takedown_request(self, takedown_processor, sample_takedown_request):
        """Test takedown request validation."""
        # Valid request
        is_valid, errors = takedown_processor._validate_takedown_request(sample_takedown_request)
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid request - missing required fields
        invalid_request = TakedownCreate(
            profile_id=1,
            infringing_url="",  # Empty URL
            original_work_title="",  # Empty title
            copyright_owner="Test Creator",
            contact_email="invalid-email",  # Invalid email
            infringement_description="",  # Empty description
            good_faith_statement=False,  # False statement
            accuracy_statement=True,
            signature=""  # Empty signature
        )
        
        is_valid, errors = takedown_processor._validate_takedown_request(invalid_request)
        assert is_valid is False
        assert len(errors) > 0

    def test_estimate_success_probability(self, takedown_processor, mock_hosting_provider_data):
        """Test takedown success probability estimation."""
        probability = takedown_processor._estimate_success_probability(
            mock_hosting_provider_data,
            evidence_quality=0.9,
            legal_strength=0.8
        )
        
        assert 0.0 <= probability <= 1.0
        # Should consider provider success rate
        assert probability > 0.5  # Given good provider success rate


@pytest.mark.unit
@pytest.mark.dmca
class TestDMCAServiceIntegration:
    """Test DMCA service integration functionality."""

    @pytest.fixture
    def dmca_integration(self):
        """Create DMCA service integration instance."""
        return DMCAServiceIntegration()

    @pytest.fixture
    def mock_whois_data(self):
        """Mock WHOIS data."""
        return {
            "domain_name": "piracy-site.com",
            "registrar": "Example Registrar",
            "creation_date": "2020-01-01",
            "expiration_date": "2025-01-01",
            "name_servers": ["ns1.hosting-provider.com"],
            "emails": ["admin@piracy-site.com"]
        }

    @pytest.mark.asyncio
    async def test_lookup_hosting_provider_by_domain(self, dmca_integration, mock_whois_data):
        """Test hosting provider lookup by domain."""
        domain = "piracy-site.com"
        
        with patch('whois.whois') as mock_whois:
            mock_whois.return_value = mock_whois_data
            
            with patch.object(dmca_integration, '_resolve_hosting_provider') as mock_resolve:
                mock_resolve.return_value = {
                    "name": "Example Hosting",
                    "dmca_email": "dmca@example-hosting.com",
                    "response_time": "3-5 days"
                }
                
                provider = await dmca_integration.lookup_hosting_provider(domain)
                
                assert provider is not None
                assert provider["name"] == "Example Hosting"
                assert "dmca_email" in provider

    @pytest.mark.asyncio
    async def test_submit_to_dmca_service(self, dmca_integration):
        """Test submission to external DMCA service."""
        takedown_data = {
            "infringing_url": "https://piracy-site.com/stolen",
            "original_url": "https://original-site.com/content",
            "copyright_owner": "Test Creator",
            "contact_email": "creator@example.com"
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "submission_id": "sub_123",
                "status": "submitted",
                "estimated_processing_time": "24-48 hours"
            }
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await dmca_integration.submit_to_dmca_service(takedown_data)
            
            assert result["submission_id"] == "sub_123"
            assert result["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_get_dmca_service_status(self, dmca_integration):
        """Test getting status from DMCA service."""
        submission_id = "sub_123"
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "submission_id": submission_id,
                "status": "processing",
                "notices_sent": 2,
                "successful_removals": 1
            }
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            status = await dmca_integration.get_dmca_service_status(submission_id)
            
            assert status["submission_id"] == submission_id
            assert status["notices_sent"] == 2

    @pytest.mark.asyncio
    async def test_handle_hosting_provider_response(self, dmca_integration):
        """Test handling hosting provider response."""
        response_data = {
            "takedown_id": "td_123",
            "provider_response": "Content removed",
            "action_taken": "content_disabled",
            "response_time": "2 days"
        }
        
        with patch.object(dmca_integration, '_update_takedown_status') as mock_update:
            mock_update.return_value = True
            
            result = await dmca_integration.handle_provider_response(response_data)
            
            assert result is True
            mock_update.assert_called_once()

    def test_parse_hosting_provider_response(self, dmca_integration):
        """Test parsing hosting provider response email."""
        email_content = """
        Thank you for your DMCA takedown notice.
        
        Case ID: CASE-123
        Status: Content Removed
        Action: The reported content has been disabled
        Date: 2024-01-15
        
        Best regards,
        DMCA Team
        """
        
        parsed = dmca_integration._parse_provider_response(email_content)
        
        assert parsed["case_id"] == "CASE-123"
        assert parsed["status"] == "Content Removed"
        assert parsed["action"] == "The reported content has been disabled"

    def test_calculate_response_metrics(self, dmca_integration):
        """Test calculation of response metrics."""
        takedown_data = [
            {
                "sent_at": datetime.utcnow() - timedelta(days=5),
                "responded_at": datetime.utcnow() - timedelta(days=3),
                "status": "successful"
            },
            {
                "sent_at": datetime.utcnow() - timedelta(days=10),
                "responded_at": datetime.utcnow() - timedelta(days=8),
                "status": "successful"
            },
            {
                "sent_at": datetime.utcnow() - timedelta(days=15),
                "responded_at": None,
                "status": "pending"
            }
        ]
        
        metrics = dmca_integration._calculate_response_metrics(takedown_data)
        
        assert metrics["total_sent"] == 3
        assert metrics["total_responded"] == 2
        assert metrics["success_rate"] == 2/3
        assert metrics["average_response_time_days"] == 2.0


@pytest.mark.unit
@pytest.mark.dmca
class TestAlertSystem:
    """Test alert and notification system for DMCA processes."""

    @pytest.fixture
    def alert_system(self):
        """Create alert system instance."""
        return AlertSystem()

    @pytest.fixture
    def mock_email_service(self):
        """Mock email service."""
        service = AsyncMock()
        service.send_email.return_value = {"message_id": "msg_123", "status": "sent"}
        return service

    @pytest.mark.asyncio
    async def test_send_takedown_submitted_alert(self, alert_system, mock_email_service):
        """Test sending takedown submitted alert."""
        takedown_data = {
            "id": "td_123",
            "infringing_url": "https://piracy-site.com/stolen",
            "status": "submitted",
            "sent_at": datetime.utcnow()
        }
        user_email = "creator@example.com"
        
        with patch.object(alert_system, 'email_service', mock_email_service):
            result = await alert_system.send_takedown_submitted_alert(
                takedown_data, 
                user_email
            )
            
            assert result["status"] == "sent"
            mock_email_service.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_takedown_successful_alert(self, alert_system, mock_email_service):
        """Test sending takedown successful alert."""
        takedown_data = {
            "id": "td_123",
            "infringing_url": "https://piracy-site.com/stolen",
            "status": "successful",
            "completed_at": datetime.utcnow()
        }
        user_email = "creator@example.com"
        
        with patch.object(alert_system, 'email_service', mock_email_service):
            result = await alert_system.send_takedown_successful_alert(
                takedown_data,
                user_email
            )
            
            assert result["status"] == "sent"
            mock_email_service.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_takedown_failed_alert(self, alert_system, mock_email_service):
        """Test sending takedown failed alert."""
        takedown_data = {
            "id": "td_123",
            "infringing_url": "https://piracy-site.com/stolen",
            "status": "failed",
            "failure_reason": "Invalid DMCA notice"
        }
        user_email = "creator@example.com"
        
        with patch.object(alert_system, 'email_service', mock_email_service):
            result = await alert_system.send_takedown_failed_alert(
                takedown_data,
                user_email
            )
            
            assert result["status"] == "sent"
            mock_email_service.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_weekly_summary_report(self, alert_system, mock_email_service):
        """Test sending weekly summary report."""
        summary_data = {
            "period": "2024-01-01 to 2024-01-07",
            "total_takedowns": 10,
            "successful": 8,
            "pending": 1,
            "failed": 1,
            "success_rate": 0.8,
            "top_infringers": ["piracy-site1.com", "piracy-site2.com"]
        }
        user_email = "creator@example.com"
        
        with patch.object(alert_system, 'email_service', mock_email_service):
            result = await alert_system.send_weekly_summary_report(
                summary_data,
                user_email
            )
            
            assert result["status"] == "sent"
            mock_email_service.send_email.assert_called_once()

    def test_format_takedown_alert_content(self, alert_system):
        """Test formatting of takedown alert content."""
        takedown_data = {
            "id": "td_123",
            "infringing_url": "https://piracy-site.com/stolen",
            "original_work_title": "My Content",
            "status": "submitted"
        }
        
        content = alert_system._format_takedown_alert(takedown_data)
        
        assert "td_123" in content
        assert "piracy-site.com" in content
        assert "My Content" in content
        assert "submitted" in content

    def test_prioritize_alerts(self, alert_system):
        """Test alert prioritization."""
        alerts = [
            {"type": "takedown_failed", "priority": 1},
            {"type": "takedown_submitted", "priority": 3},
            {"type": "takedown_successful", "priority": 2}
        ]
        
        prioritized = alert_system._prioritize_alerts(alerts)
        
        # Should be sorted by priority (1 = highest)
        assert prioritized[0]["type"] == "takedown_failed"
        assert prioritized[1]["type"] == "takedown_successful"
        assert prioritized[2]["type"] == "takedown_submitted"


@pytest.mark.integration
@pytest.mark.dmca
class TestDMCAIntegration:
    """Integration tests for DMCA services."""

    @pytest.mark.asyncio
    async def test_end_to_end_takedown_process(self, db_session, sample_takedown_request):
        """Test complete takedown process from request to completion."""
        processor = TakedownProcessor()
        integration = DMCAServiceIntegration()
        alert_system = AlertSystem()
        
        # Mock external services
        with patch.object(processor, '_send_takedown_notice') as mock_send:
            mock_send.return_value = {
                "success": True,
                "message_id": "msg_123"
            }
            
            with patch.object(alert_system, 'send_takedown_submitted_alert') as mock_alert:
                mock_alert.return_value = {"status": "sent"}
                
                # Process takedown
                result = await processor.process_takedown(sample_takedown_request)
                
                assert result["status"] == "submitted"
                
                # Send alert
                await alert_system.send_takedown_submitted_alert(
                    result,
                    sample_takedown_request.contact_email
                )
                
                mock_alert.assert_called_once()


@pytest.mark.performance
@pytest.mark.dmca
class TestDMCAPerformance:
    """Performance tests for DMCA services."""

    @pytest.mark.asyncio
    async def test_batch_takedown_processing_performance(self, sample_takedown_request):
        """Test performance of batch takedown processing."""
        import time
        
        processor = TakedownProcessor()
        requests = [sample_takedown_request for _ in range(20)]
        
        with patch.object(processor, 'process_takedown') as mock_process:
            mock_process.return_value = {"status": "submitted"}
            
            start_time = time.time()
            results = await processor.batch_process_takedowns(requests)
            end_time = time.time()
            
            assert len(results) == 20
            assert (end_time - start_time) < 10  # Should complete within 10 seconds

    @pytest.mark.asyncio
    async def test_concurrent_notice_generation(self, sample_takedown_request):
        """Test concurrent DMCA notice generation."""
        processor = TakedownProcessor()
        
        # Generate multiple notices concurrently
        tasks = []
        for _ in range(10):
            task = processor._generate_dmca_notice(sample_takedown_request)
            tasks.append(task)
        
        notices = await asyncio.gather(*tasks)
        
        assert len(notices) == 10
        assert all(notice is not None for notice in notices)


@pytest.mark.security
@pytest.mark.dmca
class TestDMCASecurity:
    """Security tests for DMCA services."""

    @pytest.mark.asyncio
    async def test_takedown_request_sanitization(self, takedown_processor):
        """Test sanitization of takedown request data."""
        malicious_request = TakedownCreate(
            profile_id=1,
            infringing_url="https://evil-site.com/<script>alert('xss')</script>",
            original_work_title="My Content<script>alert('xss')</script>",
            copyright_owner="Test Creator<script>alert('xss')</script>",
            contact_email="creator@example.com",
            infringement_description="Description<script>alert('xss')</script>",
            good_faith_statement=True,
            accuracy_statement=True,
            signature="Signature<script>alert('xss')</script>"
        )
        
        with patch.object(takedown_processor, '_sanitize_input') as mock_sanitize:
            mock_sanitize.side_effect = lambda x: x.replace("<script>", "").replace("</script>", "")
            
            sanitized = takedown_processor._sanitize_takedown_request(malicious_request)
            
            assert "<script>" not in sanitized.infringing_url
            assert "<script>" not in sanitized.original_work_title
            assert "<script>" not in sanitized.copyright_owner

    @pytest.mark.asyncio
    async def test_email_injection_prevention(self, takedown_processor):
        """Test prevention of email injection attacks."""
        malicious_data = {
            "recipient": "dmca@provider.com\nBcc: attacker@evil.com",
            "subject": "DMCA Notice\nBcc: attacker@evil.com",
            "body": "Notice content\n\nBcc: attacker@evil.com"
        }
        
        sanitized = takedown_processor._sanitize_email_data(malicious_data)
        
        assert "\n" not in sanitized["recipient"]
        assert "Bcc:" not in sanitized["subject"]
        assert sanitized["body"].count("\n") == 1  # Only original line breaks allowed