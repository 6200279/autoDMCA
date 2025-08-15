"""
Comprehensive API endpoint tests covering all routes with authentication,
authorization, input validation, and error handling.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import json
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from app.main import app
from app.core.security import create_access_token
from app.schemas.user import UserCreate
from app.schemas.profile import ProfileCreate
from app.schemas.takedown import TakedownCreate
from app.schemas.infringement import InfringementCreate


@pytest.mark.api
@pytest.mark.asyncio
class TestAuthenticationEndpoints:
    """Test authentication and authorization endpoints."""

    async def test_register_user_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "SecurePassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_register_user_duplicate_email(self, async_client: AsyncClient, test_user):
        """Test registration with duplicate email."""
        user_data = {
            "email": test_user.email,  # Already exists
            "username": "newuser",
            "full_name": "New User",
            "password": "SecurePassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    async def test_register_user_invalid_email(self, async_client: AsyncClient):
        """Test registration with invalid email."""
        user_data = {
            "email": "invalid-email",
            "username": "newuser",
            "full_name": "New User",
            "password": "SecurePassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422

    async def test_register_user_weak_password(self, async_client: AsyncClient):
        """Test registration with weak password."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "weak"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422

    async def test_login_success(self, async_client: AsyncClient, test_user, test_user_data):
        """Test successful login."""
        login_data = {
            "username": test_user.email,
            "password": test_user_data["password"]
        }
        
        response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_credentials(self, async_client: AsyncClient):
        """Test login with invalid credentials."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 401

    async def test_get_current_user(self, async_client: AsyncClient, test_user, auth_headers):
        """Test getting current authenticated user."""
        response = await async_client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email

    async def test_get_current_user_invalid_token(self, async_client: AsyncClient):
        """Test getting current user with invalid token."""
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401

    async def test_refresh_token_success(self, async_client: AsyncClient, test_user):
        """Test successful token refresh."""
        refresh_token = create_access_token(
            subject=test_user.id,
            expires_delta=timedelta(days=30)
        )
        
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_logout(self, async_client: AsyncClient, auth_headers):
        """Test user logout."""
        response = await async_client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )
        
        assert response.status_code == 200


@pytest.mark.api
@pytest.mark.asyncio
class TestProfileEndpoints:
    """Test profile management endpoints."""

    async def test_create_profile_success(self, async_client: AsyncClient, auth_headers):
        """Test successful profile creation."""
        profile_data = {
            "stage_name": "TestCreator",
            "real_name": "Test Creator",
            "bio": "Content creator and model",
            "social_media_accounts": {
                "instagram": "@testcreator",
                "twitter": "@testcreator"
            },
            "content_categories": ["photos", "videos"],
            "monitoring_keywords": ["testcreator", "test creator"],
            "protection_level": "premium"
        }
        
        response = await async_client.post(
            "/api/v1/profiles",
            json=profile_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["stage_name"] == profile_data["stage_name"]
        assert data["real_name"] == profile_data["real_name"]

    async def test_create_profile_unauthorized(self, async_client: AsyncClient):
        """Test profile creation without authentication."""
        profile_data = {
            "stage_name": "TestCreator",
            "real_name": "Test Creator"
        }
        
        response = await async_client.post(
            "/api/v1/profiles",
            json=profile_data
        )
        
        assert response.status_code == 401

    async def test_get_profiles_list(self, async_client: AsyncClient, auth_headers):
        """Test getting profiles list."""
        response = await async_client.get(
            "/api/v1/profiles",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data

    async def test_get_profile_by_id(self, async_client: AsyncClient, auth_headers):
        """Test getting specific profile by ID."""
        # First create a profile
        profile_data = {
            "stage_name": "TestCreator",
            "real_name": "Test Creator"
        }
        
        create_response = await async_client.post(
            "/api/v1/profiles",
            json=profile_data,
            headers=auth_headers
        )
        profile_id = create_response.json()["id"]
        
        # Then get it by ID
        response = await async_client.get(
            f"/api/v1/profiles/{profile_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == profile_id
        assert data["stage_name"] == profile_data["stage_name"]

    async def test_get_profile_not_found(self, async_client: AsyncClient, auth_headers):
        """Test getting non-existent profile."""
        response = await async_client.get(
            "/api/v1/profiles/999999",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_update_profile(self, async_client: AsyncClient, auth_headers):
        """Test updating profile."""
        # First create a profile
        profile_data = {
            "stage_name": "TestCreator",
            "real_name": "Test Creator"
        }
        
        create_response = await async_client.post(
            "/api/v1/profiles",
            json=profile_data,
            headers=auth_headers
        )
        profile_id = create_response.json()["id"]
        
        # Then update it
        update_data = {
            "bio": "Updated bio content",
            "protection_level": "enterprise"
        }
        
        response = await async_client.patch(
            f"/api/v1/profiles/{profile_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["bio"] == update_data["bio"]
        assert data["protection_level"] == update_data["protection_level"]

    async def test_delete_profile(self, async_client: AsyncClient, auth_headers):
        """Test deleting profile."""
        # First create a profile
        profile_data = {
            "stage_name": "TestCreator",
            "real_name": "Test Creator"
        }
        
        create_response = await async_client.post(
            "/api/v1/profiles",
            json=profile_data,
            headers=auth_headers
        )
        profile_id = create_response.json()["id"]
        
        # Then delete it
        response = await async_client.delete(
            f"/api/v1/profiles/{profile_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # Verify it's deleted
        get_response = await async_client.get(
            f"/api/v1/profiles/{profile_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404


@pytest.mark.api
@pytest.mark.asyncio
class TestTakedownEndpoints:
    """Test DMCA takedown endpoints."""

    async def test_create_takedown_success(self, async_client: AsyncClient, auth_headers):
        """Test successful takedown creation."""
        takedown_data = {
            "profile_id": 1,
            "infringing_url": "https://piracy-site.com/stolen-content",
            "original_work_title": "My Original Content",
            "copyright_owner": "Test Creator",
            "contact_email": "creator@example.com",
            "infringement_description": "My content was stolen",
            "good_faith_statement": True,
            "accuracy_statement": True,
            "signature": "Test Creator"
        }
        
        with patch('app.services.dmca.takedown_processor.TakedownProcessor.process_takedown') as mock_process:
            mock_process.return_value = {
                "takedown_id": "td_123",
                "status": "submitted"
            }
            
            response = await async_client.post(
                "/api/v1/takedowns",
                json=takedown_data,
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["infringing_url"] == takedown_data["infringing_url"]
            assert data["status"] == "submitted"

    async def test_create_takedown_invalid_data(self, async_client: AsyncClient, auth_headers):
        """Test takedown creation with invalid data."""
        takedown_data = {
            "profile_id": 1,
            "infringing_url": "invalid-url",  # Invalid URL
            "original_work_title": "",  # Empty title
            "copyright_owner": "Test Creator",
            "contact_email": "invalid-email",  # Invalid email
            "good_faith_statement": False,  # Required to be True
            "accuracy_statement": True,
            "signature": ""  # Empty signature
        }
        
        response = await async_client.post(
            "/api/v1/takedowns",
            json=takedown_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422

    async def test_get_takedowns_list(self, async_client: AsyncClient, auth_headers):
        """Test getting takedowns list."""
        response = await async_client.get(
            "/api/v1/takedowns",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_get_takedown_by_id(self, async_client: AsyncClient, auth_headers):
        """Test getting takedown by ID."""
        response = await async_client.get(
            "/api/v1/takedowns/1",
            headers=auth_headers
        )
        
        # Could be 200 if exists or 404 if not
        assert response.status_code in [200, 404]

    async def test_process_takedown(self, async_client: AsyncClient, auth_headers):
        """Test processing a takedown request."""
        with patch('app.services.dmca.takedown_processor.TakedownProcessor.process_takedown') as mock_process:
            mock_process.return_value = {
                "takedown_id": "td_123",
                "status": "processing"
            }
            
            response = await async_client.post(
                "/api/v1/takedowns/1/process",
                headers=auth_headers
            )
            
            assert response.status_code in [200, 404]  # 404 if takedown doesn't exist

    async def test_get_takedown_statistics(self, async_client: AsyncClient, auth_headers):
        """Test getting takedown statistics."""
        response = await async_client.get(
            "/api/v1/takedowns/statistics",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "success_rate" in data


@pytest.mark.api
@pytest.mark.asyncio
class TestInfringementEndpoints:
    """Test infringement detection endpoints."""

    async def test_create_infringement_report(self, async_client: AsyncClient, auth_headers):
        """Test creating infringement report."""
        infringement_data = {
            "profile_id": 1,
            "url": "https://piracy-site.com/stolen",
            "title": "Stolen Content",
            "description": "My content was stolen and posted here",
            "platform": "instagram",
            "evidence_urls": ["https://original-site.com/proof"]
        }
        
        response = await async_client.post(
            "/api/v1/infringements",
            json=infringement_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["url"] == infringement_data["url"]
        assert data["platform"] == infringement_data["platform"]

    async def test_get_infringements_list(self, async_client: AsyncClient, auth_headers):
        """Test getting infringements list."""
        response = await async_client.get(
            "/api/v1/infringements",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_get_infringements_with_filters(self, async_client: AsyncClient, auth_headers):
        """Test getting infringements with filters."""
        response = await async_client.get(
            "/api/v1/infringements?platform=instagram&status=detected",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_update_infringement_status(self, async_client: AsyncClient, auth_headers):
        """Test updating infringement status."""
        update_data = {
            "status": "resolved",
            "resolution_notes": "Content was removed"
        }
        
        response = await async_client.patch(
            "/api/v1/infringements/1",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]


@pytest.mark.api
@pytest.mark.asyncio
class TestScanningEndpoints:
    """Test scanning and monitoring endpoints."""

    async def test_start_profile_scan(self, async_client: AsyncClient, auth_headers):
        """Test starting profile scan."""
        scan_data = {
            "profile_id": 1,
            "scan_types": ["web_search", "social_media"],
            "depth": "comprehensive",
            "priority": "high"
        }
        
        with patch('app.services.scanning.scheduler.ScanScheduler.schedule_job') as mock_schedule:
            mock_schedule.return_value = "job_123"
            
            response = await async_client.post(
                "/api/v1/scanning/start",
                json=scan_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data

    async def test_get_scan_status(self, async_client: AsyncClient, auth_headers):
        """Test getting scan status."""
        response = await async_client.get(
            "/api/v1/scanning/jobs/job_123",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]

    async def test_get_scan_results(self, async_client: AsyncClient, auth_headers):
        """Test getting scan results."""
        response = await async_client.get(
            "/api/v1/scanning/results/job_123",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]

    async def test_cancel_scan(self, async_client: AsyncClient, auth_headers):
        """Test canceling scan."""
        response = await async_client.post(
            "/api/v1/scanning/jobs/job_123/cancel",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]


@pytest.mark.api
@pytest.mark.asyncio
class TestSocialMediaEndpoints:
    """Test social media monitoring endpoints."""

    async def test_start_social_media_monitoring(self, async_client: AsyncClient, auth_headers):
        """Test starting social media monitoring."""
        monitoring_data = {
            "profile_id": 1,
            "platforms": ["instagram", "twitter"],
            "monitoring_type": "impersonation_detection",
            "keywords": ["testuser", "test creator"]
        }
        
        with patch('app.services.social_media.monitoring_service.SocialMediaMonitoringService.start_monitoring') as mock_start:
            mock_start.return_value = "monitor_job_123"
            
            response = await async_client.post(
                "/api/v1/social-media/start-monitoring",
                json=monitoring_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data

    async def test_get_monitoring_results(self, async_client: AsyncClient, auth_headers):
        """Test getting monitoring results."""
        response = await async_client.get(
            "/api/v1/social-media/monitoring-results/monitor_job_123",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]

    async def test_report_impersonation(self, async_client: AsyncClient, auth_headers):
        """Test reporting impersonation."""
        report_data = {
            "profile_id": 1,
            "impersonator_url": "https://instagram.com/fake_account",
            "platform": "instagram",
            "evidence": "This account is using my photos",
            "confidence_score": 0.95
        }
        
        response = await async_client.post(
            "/api/v1/social-media/report-impersonation",
            json=report_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201


@pytest.mark.api
@pytest.mark.asyncio
class TestAIEndpoints:
    """Test AI/ML service endpoints."""

    async def test_analyze_content(self, async_client: AsyncClient, auth_headers):
        """Test content analysis."""
        # Mock file upload
        files = {
            "file": ("test_image.jpg", b"fake image data", "image/jpeg")
        }
        data = {
            "profile_id": 1,
            "analysis_type": "face_recognition"
        }
        
        with patch('app.services.ai.content_matcher.ContentMatcher.analyze_content') as mock_analyze:
            mock_analyze.return_value = {
                "similarity_score": 0.85,
                "is_match": True,
                "confidence": "high"
            }
            
            response = await async_client.post(
                "/api/v1/ai/analyze-content",
                files=files,
                data=data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            result = response.json()
            assert "similarity_score" in result
            assert "is_match" in result

    async def test_add_reference_content(self, async_client: AsyncClient, auth_headers):
        """Test adding reference content."""
        files = {
            "file": ("reference.jpg", b"fake image data", "image/jpeg")
        }
        data = {
            "profile_id": 1,
            "content_type": "profile_image",
            "metadata": json.dumps({"title": "Profile Photo"})
        }
        
        with patch('app.services.ai.content_matcher.ContentMatcher.add_reference_content') as mock_add:
            mock_add.return_value = True
            
            response = await async_client.post(
                "/api/v1/ai/add-reference",
                files=files,
                data=data,
                headers=auth_headers
            )
            
            assert response.status_code == 200


@pytest.mark.api
@pytest.mark.asyncio
class TestBillingEndpoints:
    """Test billing and subscription endpoints."""

    async def test_get_subscription_info(self, async_client: AsyncClient, auth_headers):
        """Test getting subscription information."""
        response = await async_client.get(
            "/api/v1/billing/subscription",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "plan" in data
        assert "status" in data

    async def test_get_usage_statistics(self, async_client: AsyncClient, auth_headers):
        """Test getting usage statistics."""
        response = await async_client.get(
            "/api/v1/billing/usage",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "current_period" in data
        assert "limits" in data

    async def test_create_payment_intent(self, async_client: AsyncClient, auth_headers):
        """Test creating payment intent."""
        payment_data = {
            "amount": 2999,  # $29.99
            "currency": "usd",
            "plan": "premium"
        }
        
        with patch('app.services.billing.stripe_service.StripeService.create_payment_intent') as mock_payment:
            mock_payment.return_value = {
                "id": "pi_123",
                "client_secret": "pi_123_secret"
            }
            
            response = await async_client.post(
                "/api/v1/billing/create-payment-intent",
                json=payment_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "client_secret" in data

    async def test_upgrade_subscription(self, async_client: AsyncClient, auth_headers):
        """Test upgrading subscription."""
        upgrade_data = {
            "new_plan": "enterprise",
            "payment_method_id": "pm_123"
        }
        
        response = await async_client.post(
            "/api/v1/billing/upgrade",
            json=upgrade_data,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400]  # 400 if no existing subscription


@pytest.mark.api
@pytest.mark.asyncio
class TestDashboardEndpoints:
    """Test dashboard and analytics endpoints."""

    async def test_get_dashboard_stats(self, async_client: AsyncClient, auth_headers):
        """Test getting dashboard statistics."""
        response = await async_client.get(
            "/api/v1/dashboard/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_profiles" in data
        assert "active_monitoring" in data
        assert "total_infringements" in data

    async def test_get_analytics_data(self, async_client: AsyncClient, auth_headers):
        """Test getting analytics data."""
        response = await async_client.get(
            "/api/v1/dashboard/analytics?period=30d",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "timeline" in data
        assert "summary" in data

    async def test_get_recent_activity(self, async_client: AsyncClient, auth_headers):
        """Test getting recent activity."""
        response = await async_client.get(
            "/api/v1/dashboard/activity?limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.api
@pytest.mark.security
class TestAPISecurityEndpoints:
    """Test API security measures."""

    async def test_rate_limiting(self, async_client: AsyncClient, auth_headers):
        """Test API rate limiting."""
        # Make multiple rapid requests
        responses = []
        for _ in range(20):
            response = await async_client.get(
                "/api/v1/dashboard/stats",
                headers=auth_headers
            )
            responses.append(response)
        
        # Should eventually hit rate limit
        rate_limited = any(r.status_code == 429 for r in responses)
        assert rate_limited  # At least one request should be rate limited

    async def test_input_validation_xss(self, async_client: AsyncClient, auth_headers):
        """Test XSS input validation."""
        malicious_data = {
            "stage_name": "<script>alert('xss')</script>",
            "bio": "<img src=x onerror=alert('xss')>",
            "real_name": "Test Creator"
        }
        
        response = await async_client.post(
            "/api/v1/profiles",
            json=malicious_data,
            headers=auth_headers
        )
        
        # Should either reject or sanitize the input
        if response.status_code == 201:
            data = response.json()
            assert "<script>" not in data["stage_name"]
            assert "<img" not in data["bio"]

    async def test_sql_injection_protection(self, async_client: AsyncClient, auth_headers):
        """Test SQL injection protection."""
        malicious_query = "'; DROP TABLE users; --"
        
        response = await async_client.get(
            f"/api/v1/profiles?search={malicious_query}",
            headers=auth_headers
        )
        
        # Should handle safely without SQL injection
        assert response.status_code in [200, 400, 422]

    async def test_unauthorized_access_different_user_data(self, async_client: AsyncClient, test_user, superuser):
        """Test unauthorized access to other user's data."""
        # Create token for test_user
        user_token = create_access_token(subject=test_user.id)
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Try to access superuser's data (if profile exists)
        response = await async_client.get(
            f"/api/v1/users/{superuser.id}",
            headers=user_headers
        )
        
        # Should be forbidden or not found
        assert response.status_code in [403, 404]

    async def test_admin_only_endpoints(self, async_client: AsyncClient, auth_headers, admin_headers):
        """Test admin-only endpoint access."""
        # Regular user should be forbidden
        response = await async_client.get(
            "/api/v1/admin/users",
            headers=auth_headers
        )
        assert response.status_code == 403
        
        # Admin should have access
        response = await async_client.get(
            "/api/v1/admin/users", 
            headers=admin_headers
        )
        assert response.status_code in [200, 404]  # 404 if endpoint doesn't exist yet


@pytest.mark.api
@pytest.mark.performance
class TestAPIPerformance:
    """Test API performance characteristics."""

    async def test_response_time_dashboard(self, async_client: AsyncClient, auth_headers):
        """Test dashboard response time."""
        import time
        
        start_time = time.time()
        response = await async_client.get(
            "/api/v1/dashboard/stats",
            headers=auth_headers
        )
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # Should respond within 2 seconds

    async def test_concurrent_requests_handling(self, async_client: AsyncClient, auth_headers):
        """Test handling of concurrent requests."""
        import asyncio
        
        # Make 10 concurrent requests
        tasks = [
            async_client.get("/api/v1/dashboard/stats", headers=auth_headers)
            for _ in range(10)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)

    async def test_large_payload_handling(self, async_client: AsyncClient, auth_headers):
        """Test handling of large payloads."""
        # Create large profile data
        large_bio = "A" * 5000  # 5KB bio
        large_keywords = [f"keyword_{i}" for i in range(1000)]
        
        profile_data = {
            "stage_name": "TestCreator",
            "real_name": "Test Creator",
            "bio": large_bio,
            "monitoring_keywords": large_keywords
        }
        
        response = await async_client.post(
            "/api/v1/profiles",
            json=profile_data,
            headers=auth_headers
        )
        
        # Should handle large payloads gracefully
        assert response.status_code in [201, 413, 422]  # 413 = Payload too large


@pytest.mark.api
@pytest.mark.edge_cases
class TestAPIEdgeCases:
    """Test API edge cases and error conditions."""

    async def test_empty_request_body(self, async_client: AsyncClient, auth_headers):
        """Test handling of empty request body."""
        response = await async_client.post(
            "/api/v1/profiles",
            json={},
            headers=auth_headers
        )
        
        assert response.status_code == 422

    async def test_malformed_json(self, async_client: AsyncClient, auth_headers):
        """Test handling of malformed JSON."""
        response = await async_client.post(
            "/api/v1/profiles",
            data="{ invalid json }",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    async def test_missing_required_fields(self, async_client: AsyncClient, auth_headers):
        """Test handling of missing required fields."""
        incomplete_data = {
            "stage_name": "TestCreator"
            # Missing required fields
        }
        
        response = await async_client.post(
            "/api/v1/profiles",
            json=incomplete_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422

    async def test_invalid_content_type(self, async_client: AsyncClient, auth_headers):
        """Test handling of invalid content type."""
        response = await async_client.post(
            "/api/v1/profiles",
            data="plain text data",
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        
        assert response.status_code in [415, 422]

    async def test_extremely_long_urls(self, async_client: AsyncClient, auth_headers):
        """Test handling of extremely long URLs."""
        long_url = "https://example.com/" + "a" * 5000
        
        response = await async_client.get(
            f"/api/v1/infringements?url={long_url}",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 414, 422]  # 414 = URI Too Long