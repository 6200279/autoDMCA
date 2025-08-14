"""
Comprehensive tests for DMCA takedown API endpoints.
Tests takedown creation, processing, status tracking, and compliance features.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from fastapi import status
from httpx import AsyncClient

from app.models.takedown import TakedownRequest, TakedownStatus, TakedownMethod
from app.models.infringement import Infringement
from app.models.profile import ProtectedProfile


@pytest.mark.api
@pytest.mark.unit
class TestTakedownAPI:
    """Test DMCA takedown API endpoints."""

    @pytest.mark.asyncio
    async def test_create_takedown_request_success(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test successful takedown request creation."""
        # Create a profile for the user
        profile = ProtectedProfile(
            user_id=test_user.id,
            stage_name="TestCreator",
            real_name="Test Creator",
            bio="Test bio"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        takedown_data = {
            "profile_id": profile.id,
            "infringing_url": "https://leak-site.com/stolen-content",
            "original_work_title": "My Original Content",
            "copyright_owner": "Test Creator",
            "infringement_description": "Unauthorized distribution of my copyrighted material",
            "contact_info": {
                "name": "Test Creator",
                "email": "creator@test.com",
                "address": "123 Test St, Test City, TC 12345"
            },
            "signature": "Test Creator",
            "method": "email"
        }
        
        response = await async_client.post(
            "/api/v1/takedowns/",
            json=takedown_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["infringing_url"] == takedown_data["infringing_url"]
        assert data["status"] == TakedownStatus.PENDING.value
        assert "takedown_id" in data

    @pytest.mark.asyncio
    async def test_create_takedown_invalid_profile(self, async_client: AsyncClient, auth_headers):
        """Test takedown creation with invalid profile ID."""
        takedown_data = {
            "profile_id": 99999,  # Non-existent profile
            "infringing_url": "https://leak-site.com/stolen-content",
            "original_work_title": "My Original Content",
            "copyright_owner": "Test Creator",
            "infringement_description": "Unauthorized distribution",
            "contact_info": {
                "name": "Test Creator",
                "email": "creator@test.com"
            },
            "signature": "Test Creator"
        }
        
        response = await async_client.post(
            "/api/v1/takedowns/",
            json=takedown_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_takedown_invalid_url(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test takedown creation with invalid URL."""
        profile = ProtectedProfile(
            user_id=test_user.id,
            stage_name="TestCreator",
            real_name="Test Creator"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        takedown_data = {
            "profile_id": profile.id,
            "infringing_url": "not-a-valid-url",
            "original_work_title": "My Original Content",
            "copyright_owner": "Test Creator",
            "infringement_description": "Unauthorized distribution",
            "contact_info": {
                "name": "Test Creator",
                "email": "creator@test.com"
            },
            "signature": "Test Creator"
        }
        
        response = await async_client.post(
            "/api/v1/takedowns/",
            json=takedown_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_takedown_requests(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test retrieving takedown requests."""
        # Create profile and takedown requests
        profile = ProtectedProfile(
            user_id=test_user.id,
            stage_name="TestCreator",
            real_name="Test Creator"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        takedown1 = TakedownRequest(
            profile_id=profile.id,
            infringing_url="https://site1.com/content",
            original_work_title="Content 1",
            copyright_owner="Test Creator",
            infringement_description="Description 1",
            status=TakedownStatus.PENDING
        )
        takedown2 = TakedownRequest(
            profile_id=profile.id,
            infringing_url="https://site2.com/content",
            original_work_title="Content 2",
            copyright_owner="Test Creator",
            infringement_description="Description 2",
            status=TakedownStatus.SENT
        )
        
        db_session.add_all([takedown1, takedown2])
        await db_session.commit()
        
        response = await async_client.get("/api/v1/takedowns/", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2
        assert "total" in data
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_get_takedown_by_id(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test retrieving specific takedown request."""
        profile = ProtectedProfile(
            user_id=test_user.id,
            stage_name="TestCreator",
            real_name="Test Creator"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        takedown = TakedownRequest(
            profile_id=profile.id,
            infringing_url="https://site.com/content",
            original_work_title="Test Content",
            copyright_owner="Test Creator",
            infringement_description="Test description",
            status=TakedownStatus.PENDING
        )
        db_session.add(takedown)
        await db_session.commit()
        await db_session.refresh(takedown)
        
        response = await async_client.get(f"/api/v1/takedowns/{takedown.id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == takedown.id
        assert data["infringing_url"] == takedown.infringing_url

    @pytest.mark.asyncio
    async def test_get_takedown_unauthorized(self, async_client: AsyncClient, auth_headers, superuser, db_session):
        """Test accessing takedown request from different user."""
        # Create profile for superuser
        profile = ProtectedProfile(
            user_id=superuser.id,
            stage_name="SuperCreator",
            real_name="Super Creator"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        takedown = TakedownRequest(
            profile_id=profile.id,
            infringing_url="https://site.com/content",
            original_work_title="Super Content",
            copyright_owner="Super Creator",
            infringement_description="Super description",
            status=TakedownStatus.PENDING
        )
        db_session.add(takedown)
        await db_session.commit()
        await db_session.refresh(takedown)
        
        # Try to access with regular user headers
        response = await async_client.get(f"/api/v1/takedowns/{takedown.id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    @patch('app.services.dmca.takedown_processor.TakedownProcessor.process_takedown')
    async def test_process_takedown_request(self, mock_process, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test processing a takedown request."""
        mock_process.return_value = {
            "status": "sent",
            "notices_sent": 1,
            "hosting_providers": ["example.com"]
        }
        
        profile = ProtectedProfile(
            user_id=test_user.id,
            stage_name="TestCreator",
            real_name="Test Creator"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        takedown = TakedownRequest(
            profile_id=profile.id,
            infringing_url="https://site.com/content",
            original_work_title="Test Content",
            copyright_owner="Test Creator",
            infringement_description="Test description",
            status=TakedownStatus.PENDING
        )
        db_session.add(takedown)
        await db_session.commit()
        await db_session.refresh(takedown)
        
        response = await async_client.post(
            f"/api/v1/takedowns/{takedown.id}/process",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Takedown request processed successfully"
        mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_takedown_status(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test updating takedown request status."""
        profile = ProtectedProfile(
            user_id=test_user.id,
            stage_name="TestCreator",
            real_name="Test Creator"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        takedown = TakedownRequest(
            profile_id=profile.id,
            infringing_url="https://site.com/content",
            original_work_title="Test Content",
            copyright_owner="Test Creator",
            infringement_description="Test description",
            status=TakedownStatus.SENT
        )
        db_session.add(takedown)
        await db_session.commit()
        await db_session.refresh(takedown)
        
        update_data = {
            "status": TakedownStatus.SUCCESSFUL.value,
            "notes": "Content successfully removed"
        }
        
        response = await async_client.patch(
            f"/api/v1/takedowns/{takedown.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == TakedownStatus.SUCCESSFUL.value
        assert data["notes"] == "Content successfully removed"

    @pytest.mark.asyncio
    async def test_bulk_create_takedowns(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test bulk creation of takedown requests."""
        profile = ProtectedProfile(
            user_id=test_user.id,
            stage_name="TestCreator",
            real_name="Test Creator"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        bulk_data = {
            "profile_id": profile.id,
            "copyright_owner": "Test Creator",
            "contact_info": {
                "name": "Test Creator",
                "email": "creator@test.com"
            },
            "signature": "Test Creator",
            "requests": [
                {
                    "infringing_url": "https://site1.com/content",
                    "original_work_title": "Content 1",
                    "infringement_description": "Description 1"
                },
                {
                    "infringing_url": "https://site2.com/content",
                    "original_work_title": "Content 2",
                    "infringement_description": "Description 2"
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/takedowns/bulk",
            json=bulk_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["created_requests"]) == 2
        assert data["total_created"] == 2

    @pytest.mark.asyncio
    async def test_get_takedown_statistics(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test retrieving takedown statistics."""
        profile = ProtectedProfile(
            user_id=test_user.id,
            stage_name="TestCreator",
            real_name="Test Creator"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        # Create takedowns with different statuses
        takedowns = [
            TakedownRequest(
                profile_id=profile.id,
                infringing_url=f"https://site{i}.com/content",
                original_work_title=f"Content {i}",
                copyright_owner="Test Creator",
                infringement_description=f"Description {i}",
                status=status_value
            )
            for i, status_value in enumerate([
                TakedownStatus.PENDING,
                TakedownStatus.SENT,
                TakedownStatus.SUCCESSFUL,
                TakedownStatus.FAILED
            ], 1)
        ]
        
        db_session.add_all(takedowns)
        await db_session.commit()
        
        response = await async_client.get("/api/v1/takedowns/statistics", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_requests" in data
        assert "status_breakdown" in data
        assert "success_rate" in data
        assert data["total_requests"] == 4


@pytest.mark.api
@pytest.mark.integration
class TestTakedownIntegration:
    """Integration tests for takedown workflows."""

    @pytest.mark.asyncio
    @patch('app.services.dmca.takedown_processor.TakedownProcessor.process_takedown')
    @patch('app.services.auth.email_service.send_dmca_notice')
    async def test_complete_takedown_workflow(self, mock_email, mock_process, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test complete takedown workflow from creation to processing."""
        mock_process.return_value = {
            "status": "sent",
            "notices_sent": 1,
            "hosting_providers": ["example.com"]
        }
        mock_email.return_value = {"message_id": "test123", "status": "sent"}
        
        # Step 1: Create profile
        profile = ProtectedProfile(
            user_id=test_user.id,
            stage_name="TestCreator",
            real_name="Test Creator"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        # Step 2: Create takedown request
        takedown_data = {
            "profile_id": profile.id,
            "infringing_url": "https://leak-site.com/stolen-content",
            "original_work_title": "My Original Content",
            "copyright_owner": "Test Creator",
            "infringement_description": "Unauthorized distribution",
            "contact_info": {
                "name": "Test Creator",
                "email": "creator@test.com"
            },
            "signature": "Test Creator"
        }
        
        create_response = await async_client.post(
            "/api/v1/takedowns/",
            json=takedown_data,
            headers=auth_headers
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        takedown_id = create_response.json()["id"]
        
        # Step 3: Process takedown request
        process_response = await async_client.post(
            f"/api/v1/takedowns/{takedown_id}/process",
            headers=auth_headers
        )
        assert process_response.status_code == status.HTTP_200_OK
        
        # Step 4: Verify status update
        get_response = await async_client.get(
            f"/api/v1/takedowns/{takedown_id}",
            headers=auth_headers
        )
        assert get_response.status_code == status.HTTP_200_OK
        updated_takedown = get_response.json()
        assert updated_takedown["status"] in [TakedownStatus.SENT.value, TakedownStatus.PROCESSING.value]

    @pytest.mark.asyncio
    async def test_takedown_filtering_and_pagination(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test takedown filtering and pagination."""
        profile = ProtectedProfile(
            user_id=test_user.id,
            stage_name="TestCreator",
            real_name="Test Creator"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        # Create takedowns with different statuses and dates
        takedowns = []
        for i in range(15):
            status_cycle = [TakedownStatus.PENDING, TakedownStatus.SENT, TakedownStatus.SUCCESSFUL]
            takedown = TakedownRequest(
                profile_id=profile.id,
                infringing_url=f"https://site{i}.com/content",
                original_work_title=f"Content {i}",
                copyright_owner="Test Creator",
                infringement_description=f"Description {i}",
                status=status_cycle[i % 3],
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            takedowns.append(takedown)
        
        db_session.add_all(takedowns)
        await db_session.commit()
        
        # Test pagination
        response = await async_client.get(
            "/api/v1/takedowns/?page=1&size=5",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 15
        
        # Test status filtering
        response = await async_client.get(
            f"/api/v1/takedowns/?status={TakedownStatus.PENDING.value}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(item["status"] == TakedownStatus.PENDING.value for item in data["items"])


@pytest.mark.api
@pytest.mark.security
class TestTakedownSecurity:
    """Security tests for takedown endpoints."""

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, async_client: AsyncClient):
        """Test unauthorized access to takedown endpoints."""
        # Try to access without authentication
        response = await async_client.get("/api/v1/takedowns/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        response = await async_client.post("/api/v1/takedowns/", json={})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_cross_user_data_access(self, async_client: AsyncClient, auth_headers, test_user, superuser, db_session):
        """Test that users cannot access other users' takedown data."""
        # Create takedown for superuser
        superuser_profile = ProtectedProfile(
            user_id=superuser.id,
            stage_name="SuperCreator",
            real_name="Super Creator"
        )
        db_session.add(superuser_profile)
        await db_session.commit()
        await db_session.refresh(superuser_profile)
        
        takedown = TakedownRequest(
            profile_id=superuser_profile.id,
            infringing_url="https://site.com/content",
            original_work_title="Super Content",
            copyright_owner="Super Creator",
            infringement_description="Super description",
            status=TakedownStatus.PENDING
        )
        db_session.add(takedown)
        await db_session.commit()
        await db_session.refresh(takedown)
        
        # Try to access with regular user credentials
        response = await async_client.get(f"/api/v1/takedowns/{takedown.id}", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_input_validation_and_sanitization(self, async_client: AsyncClient, auth_headers, test_user, db_session, security_test_payloads):
        """Test input validation and sanitization."""
        profile = ProtectedProfile(
            user_id=test_user.id,
            stage_name="TestCreator",
            real_name="Test Creator"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        # Test XSS in takedown description
        for payload in security_test_payloads["xss"]:
            takedown_data = {
                "profile_id": profile.id,
                "infringing_url": "https://site.com/content",
                "original_work_title": "Test Content",
                "copyright_owner": "Test Creator",
                "infringement_description": payload,  # XSS payload
                "contact_info": {
                    "name": "Test Creator",
                    "email": "creator@test.com"
                },
                "signature": "Test Creator"
            }
            
            response = await async_client.post(
                "/api/v1/takedowns/",
                json=takedown_data,
                headers=auth_headers
            )
            
            # Should either reject or sanitize
            if response.status_code == status.HTTP_201_CREATED:
                data = response.json()
                assert "<script>" not in data["infringement_description"]
                assert "javascript:" not in data["infringement_description"]

    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, async_client: AsyncClient, auth_headers, security_test_payloads):
        """Test SQL injection protection."""
        for payload in security_test_payloads["sql_injection"]:
            # Test in URL parameter
            response = await async_client.get(f"/api/v1/takedowns/?search={payload}", headers=auth_headers)
            
            # Should not cause internal server error
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]


@pytest.mark.api
@pytest.mark.performance
class TestTakedownPerformance:
    """Performance tests for takedown endpoints."""

    @pytest.mark.asyncio
    async def test_bulk_creation_performance(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test performance of bulk takedown creation."""
        import time
        
        profile = ProtectedProfile(
            user_id=test_user.id,
            stage_name="TestCreator",
            real_name="Test Creator"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        # Create bulk request with 50 takedowns
        bulk_data = {
            "profile_id": profile.id,
            "copyright_owner": "Test Creator",
            "contact_info": {
                "name": "Test Creator",
                "email": "creator@test.com"
            },
            "signature": "Test Creator",
            "requests": [
                {
                    "infringing_url": f"https://site{i}.com/content",
                    "original_work_title": f"Content {i}",
                    "infringement_description": f"Description {i}"
                }
                for i in range(50)
            ]
        }
        
        start_time = time.time()
        response = await async_client.post(
            "/api/v1/takedowns/bulk",
            json=bulk_data,
            headers=auth_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_201_CREATED
        assert (end_time - start_time) < 10.0  # Should complete within 10 seconds

    @pytest.mark.asyncio
    async def test_large_list_performance(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test performance with large number of takedown requests."""
        import time
        
        profile = ProtectedProfile(
            user_id=test_user.id,
            stage_name="TestCreator",
            real_name="Test Creator"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        # Create 100 takedown requests
        takedowns = [
            TakedownRequest(
                profile_id=profile.id,
                infringing_url=f"https://site{i}.com/content",
                original_work_title=f"Content {i}",
                copyright_owner="Test Creator",
                infringement_description=f"Description {i}",
                status=TakedownStatus.PENDING
            )
            for i in range(100)
        ]
        
        db_session.add_all(takedowns)
        await db_session.commit()
        
        # Test list performance
        start_time = time.time()
        response = await async_client.get("/api/v1/takedowns/?size=50", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert (end_time - start_time) < 2.0  # Should complete within 2 seconds