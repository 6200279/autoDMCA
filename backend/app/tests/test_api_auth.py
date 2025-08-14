"""
Comprehensive tests for authentication API endpoints.
Tests login, registration, password reset, 2FA, and security features.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest


@pytest.mark.api
@pytest.mark.unit
class TestAuthenticationAPI:
    """Test authentication API endpoints."""

    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient, db_session):
        """Test successful user registration."""
        registration_data = {
            "email": "newuser@test.com",
            "username": "newuser",
            "password": "StrongPassword123!",
            "full_name": "New User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=registration_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == registration_data["email"]
        assert data["user"]["username"] == registration_data["username"]
        assert "id" in data["user"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client: AsyncClient, test_user):
        """Test registration with duplicate email."""
        registration_data = {
            "email": test_user.email,  # Same email as existing user
            "username": "differentuser",
            "password": "StrongPassword123!",
            "full_name": "Different User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=registration_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, async_client: AsyncClient, test_user):
        """Test registration with duplicate username."""
        registration_data = {
            "email": "different@test.com",
            "username": test_user.username,  # Same username as existing user
            "password": "StrongPassword123!",
            "full_name": "Different User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=registration_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_weak_password(self, async_client: AsyncClient):
        """Test registration with weak password."""
        registration_data = {
            "email": "test@test.com",
            "username": "testuser",
            "password": "weak",  # Weak password
            "full_name": "Test User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=registration_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, async_client: AsyncClient):
        """Test registration with invalid email format."""
        registration_data = {
            "email": "invalid-email",
            "username": "testuser",
            "password": "StrongPassword123!",
            "full_name": "Test User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=registration_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, test_user, test_user_data):
        """Test successful login."""
        login_data = {
            "username": test_user.email,
            "password": test_user_data["password"]
        }
        
        response = await async_client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, async_client: AsyncClient, test_user):
        """Test login with invalid credentials."""
        login_data = {
            "username": test_user.email,
            "password": "wrong_password"
        }
        
        response = await async_client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with non-existent user."""
        login_data = {
            "username": "nonexistent@test.com",
            "password": "somepassword"
        }
        
        response = await async_client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, async_client: AsyncClient, db_session):
        """Test login with inactive user."""
        # Create inactive user
        inactive_user = User(
            email="inactive@test.com",
            username="inactive",
            hashed_password=get_password_hash("TestPassword123!"),
            is_active=False
        )
        db_session.add(inactive_user)
        await db_session.commit()
        
        login_data = {
            "username": "inactive@test.com",
            "password": "TestPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "inactive" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, async_client: AsyncClient, test_user):
        """Test successful token refresh."""
        # First login to get refresh token
        login_data = {
            "username": test_user.email,
            "password": "TestPassword123!"
        }
        
        login_response = await async_client.post("/api/v1/auth/login", data=login_data)
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token to get new access token
        refresh_data = {"refresh_token": refresh_token}
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """Test refresh with invalid token."""
        refresh_data = {"refresh_token": "invalid_token"}
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user(self, async_client: AsyncClient, auth_headers, test_user):
        """Test getting current user information."""
        response = await async_client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, async_client: AsyncClient):
        """Test getting current user with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_logout_success(self, async_client: AsyncClient, auth_headers):
        """Test successful logout."""
        response = await async_client.post("/api/v1/auth/logout", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Successfully logged out"

    @pytest.mark.asyncio
    async def test_change_password_success(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test successful password change."""
        password_data = {
            "current_password": "TestPassword123!",
            "new_password": "NewStrongPassword123!",
            "confirm_password": "NewStrongPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/change-password", json=password_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify password was actually changed
        await db_session.refresh(test_user)
        assert verify_password("NewStrongPassword123!", test_user.hashed_password)

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, async_client: AsyncClient, auth_headers):
        """Test password change with wrong current password."""
        password_data = {
            "current_password": "WrongPassword123!",
            "new_password": "NewStrongPassword123!",
            "confirm_password": "NewStrongPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/change-password", json=password_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_change_password_mismatch(self, async_client: AsyncClient, auth_headers):
        """Test password change with mismatched confirmation."""
        password_data = {
            "current_password": "TestPassword123!",
            "new_password": "NewStrongPassword123!",
            "confirm_password": "DifferentPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/change-password", json=password_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    @patch('app.services.auth.email_service.send_password_reset_email')
    async def test_request_password_reset(self, mock_send_email, async_client: AsyncClient, test_user):
        """Test password reset request."""
        mock_send_email.return_value = True
        
        reset_data = {"email": test_user.email}
        response = await async_client.post("/api/v1/auth/request-password-reset", json=reset_data)
        
        assert response.status_code == status.HTTP_200_OK
        assert "email sent" in response.json()["message"].lower()
        mock_send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_password_reset_nonexistent_email(self, async_client: AsyncClient):
        """Test password reset request for non-existent email."""
        reset_data = {"email": "nonexistent@test.com"}
        response = await async_client.post("/api/v1/auth/request-password-reset", json=reset_data)
        
        # Should return success to prevent email enumeration
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_enable_two_factor_auth(self, async_client: AsyncClient, auth_headers):
        """Test enabling two-factor authentication."""
        response = await async_client.post("/api/v1/auth/2fa/enable", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "secret" in data
        assert "qr_code" in data
        assert "backup_codes" in data

    @pytest.mark.asyncio
    @patch('app.core.security.verify_totp_code')
    async def test_verify_two_factor_setup(self, mock_verify_totp, async_client: AsyncClient, auth_headers):
        """Test verifying two-factor authentication setup."""
        mock_verify_totp.return_value = True
        
        verify_data = {"code": "123456"}
        response = await async_client.post("/api/v1/auth/2fa/verify-setup", json=verify_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "2FA enabled successfully"

    @pytest.mark.asyncio
    async def test_disable_two_factor_auth(self, async_client: AsyncClient, auth_headers):
        """Test disabling two-factor authentication."""
        disable_data = {"password": "TestPassword123!"}
        response = await async_client.post("/api/v1/auth/2fa/disable", json=disable_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "2FA disabled successfully"


@pytest.mark.api
@pytest.mark.integration
class TestAuthenticationIntegration:
    """Integration tests for authentication workflows."""

    @pytest.mark.asyncio
    async def test_full_registration_login_flow(self, async_client: AsyncClient, db_session):
        """Test complete registration and login flow."""
        # Step 1: Register
        registration_data = {
            "email": "integration@test.com",
            "username": "integrationuser",
            "password": "IntegrationPassword123!",
            "full_name": "Integration User"
        }
        
        register_response = await async_client.post("/api/v1/auth/register", json=registration_data)
        assert register_response.status_code == status.HTTP_201_CREATED
        
        # Step 2: Login with new credentials
        login_data = {
            "username": registration_data["email"],
            "password": registration_data["password"]
        }
        
        login_response = await async_client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == status.HTTP_200_OK
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: Access protected endpoint
        me_response = await async_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["email"] == registration_data["email"]

    @pytest.mark.asyncio
    async def test_password_change_and_relogin(self, async_client: AsyncClient, test_user, test_user_data):
        """Test password change followed by re-login with new password."""
        # Step 1: Login with original password
        login_data = {
            "username": test_user.email,
            "password": test_user_data["password"]
        }
        
        login_response = await async_client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 2: Change password
        new_password = "NewIntegrationPassword123!"
        password_data = {
            "current_password": test_user_data["password"],
            "new_password": new_password,
            "confirm_password": new_password
        }
        
        change_response = await async_client.post("/api/v1/auth/change-password", json=password_data, headers=headers)
        assert change_response.status_code == status.HTTP_200_OK
        
        # Step 3: Login with new password
        new_login_data = {
            "username": test_user.email,
            "password": new_password
        }
        
        new_login_response = await async_client.post("/api/v1/auth/login", data=new_login_data)
        assert new_login_response.status_code == status.HTTP_200_OK
        
        # Step 4: Verify old password doesn't work
        old_login_response = await async_client.post("/api/v1/auth/login", data=login_data)
        assert old_login_response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
@pytest.mark.security
class TestAuthenticationSecurity:
    """Security tests for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_sql_injection_in_login(self, async_client: AsyncClient, security_test_payloads):
        """Test SQL injection attempts in login."""
        for payload in security_test_payloads["sql_injection"]:
            login_data = {
                "username": payload,
                "password": "anypassword"
            }
            
            response = await async_client.post("/api/v1/auth/login", data=login_data)
            
            # Should not cause internal server error
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_422_UNPROCESSABLE_ENTITY]

    @pytest.mark.asyncio
    async def test_xss_in_registration(self, async_client: AsyncClient, security_test_payloads):
        """Test XSS attempts in registration."""
        for payload in security_test_payloads["xss"]:
            registration_data = {
                "email": "xsstest@test.com",
                "username": "xssuser",
                "password": "StrongPassword123!",
                "full_name": payload  # XSS payload in full name
            }
            
            response = await async_client.post("/api/v1/auth/register", json=registration_data)
            
            # Should either reject or sanitize
            if response.status_code == status.HTTP_201_CREATED:
                # If accepted, check that XSS is sanitized
                user_data = response.json()["user"]
                assert "<script>" not in user_data["full_name"]
                assert "javascript:" not in user_data["full_name"]

    @pytest.mark.asyncio
    async def test_rate_limiting_login_attempts(self, async_client: AsyncClient, test_user):
        """Test rate limiting on login attempts."""
        login_data = {
            "username": test_user.email,
            "password": "wrong_password"
        }
        
        # Make multiple failed attempts
        responses = []
        for _ in range(10):
            response = await async_client.post("/api/v1/auth/login", data=login_data)
            responses.append(response.status_code)
        
        # Should eventually get rate limited
        assert status.HTTP_429_TOO_MANY_REQUESTS in responses

    @pytest.mark.asyncio
    async def test_token_expiry(self, async_client: AsyncClient, test_user):
        """Test that expired tokens are rejected."""
        # Create an expired token
        expired_token = create_access_token(
            subject=test_user.id,
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_token_manipulation(self, async_client: AsyncClient):
        """Test that manipulated tokens are rejected."""
        # Create a token and manipulate it
        valid_token = create_access_token(subject="user123")
        manipulated_token = valid_token[:-5] + "xxxxx"  # Change last 5 characters
        
        headers = {"Authorization": f"Bearer {manipulated_token}"}
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_password_complexity_requirements(self, async_client: AsyncClient):
        """Test password complexity enforcement."""
        weak_passwords = [
            "password",      # Common password
            "12345678",      # Only numbers
            "abcdefgh",      # Only lowercase
            "ABCDEFGH",      # Only uppercase
            "Pass1",         # Too short
            "password1",     # No uppercase or special chars
        ]
        
        for weak_password in weak_passwords:
            registration_data = {
                "email": f"test{weak_password}@test.com",
                "username": f"user{weak_password}",
                "password": weak_password,
                "full_name": "Test User"
            }
            
            response = await async_client.post("/api/v1/auth/register", json=registration_data)
            
            # Should reject weak passwords
            assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.api
@pytest.mark.performance
class TestAuthenticationPerformance:
    """Performance tests for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_login_performance(self, async_client: AsyncClient, test_user, test_user_data, performance_config):
        """Test login endpoint performance."""
        import time
        
        login_data = {
            "username": test_user.email,
            "password": test_user_data["password"]
        }
        
        start_time = time.time()
        response = await async_client.post("/api/v1/auth/login", data=login_data)
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert (end_time - start_time) < performance_config["max_response_time"]

    @pytest.mark.asyncio
    async def test_concurrent_login_requests(self, async_client: AsyncClient, test_user, test_user_data):
        """Test handling of concurrent login requests."""
        import asyncio
        
        login_data = {
            "username": test_user.email,
            "password": test_user_data["password"]
        }
        
        async def make_login_request():
            return await async_client.post("/api/v1/auth/login", data=login_data)
        
        # Make 10 concurrent requests
        tasks = [make_login_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK