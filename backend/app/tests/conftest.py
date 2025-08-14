"""
Comprehensive test configuration and fixtures for the Content Protection Platform.
Provides fixtures for database testing, API testing, authentication, AI services, and more.
"""

import asyncio
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from faker import Faker
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from app.main import app
from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.db.base import Base
from app.schemas.user import UserCreate
from app.schemas.auth import Token
from app.services.ai.content_matcher import ContentMatcher
from app.services.dmca.takedown_processor import TakedownProcessor
from app.services.billing.stripe_service import StripeService
from app.services.social_media.monitoring_service import SocialMediaMonitoringService

# Initialize Faker for test data generation
fake = Faker()

# Test database configuration
TEST_DATABASE_URL = "postgresql://test:test@localhost:5432/test_autodmca"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Override settings for testing."""
    from app.core.config import Settings
    
    return Settings(
        database_url=TEST_DATABASE_URL,
        secret_key="test-secret-key-for-testing-only",
        redis_url="redis://localhost:6379/15",
        environment="testing",
        debug=True,
        testing=True,
        # Disable external services in tests
        stripe_secret_key="sk_test_fake_key",
        sendgrid_api_key="SG.fake_key",
        google_api_key="fake_google_key",
        bing_api_key="fake_bing_key",
        # AI service settings
        face_recognition_tolerance=0.6,
        image_similarity_threshold=0.85,
        ai_content_matching_enabled=True,
    )


@pytest.fixture(scope="session")
async def postgres_container():
    """Start a PostgreSQL container for testing."""
    with PostgresContainer("postgres:15") as postgres:
        yield postgres


@pytest.fixture(scope="session")
async def test_db_engine(postgres_container, test_settings):
    """Create test database engine."""
    database_url = postgres_container.get_connection_url()
    engine = create_async_engine(database_url, echo=True)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing."""
    async_session = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def override_get_db(db_session):
    """Override the get_db dependency."""
    async def _override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides = {}


@pytest.fixture
def client(override_get_db):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# User and authentication fixtures
@pytest.fixture
def test_user_data():
    """Generate test user data."""
    return {
        "email": fake.email(),
        "username": fake.user_name(),
        "full_name": fake.name(),
        "password": "TestPassword123!",
        "is_active": True,
        "is_superuser": False,
    }


@pytest.fixture
async def test_user(db_session, test_user_data):
    """Create a test user in the database."""
    from app.models.user import User
    
    user = User(
        email=test_user_data["email"],
        username=test_user_data["username"],
        full_name=test_user_data["full_name"],
        hashed_password=get_password_hash(test_user_data["password"]),
        is_active=test_user_data["is_active"],
        is_superuser=test_user_data["is_superuser"],
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest.fixture
async def superuser(db_session):
    """Create a test superuser."""
    from app.models.user import User
    
    user = User(
        email="admin@test.com",
        username="admin",
        full_name="Test Admin",
        hashed_password=get_password_hash("AdminPassword123!"),
        is_active=True,
        is_superuser=True,
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest.fixture
def user_token(test_user):
    """Create an access token for the test user."""
    return create_access_token(subject=test_user.id)


@pytest.fixture
def superuser_token(superuser):
    """Create an access token for the superuser."""
    return create_access_token(subject=superuser.id)


@pytest.fixture
def auth_headers(user_token):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(superuser_token):
    """Create admin authorization headers."""
    return {"Authorization": f"Bearer {superuser_token}"}


# AI and ML service mocks
@pytest.fixture
def mock_content_matcher():
    """Mock the AI content matcher service."""
    matcher = AsyncMock(spec=ContentMatcher)
    matcher.analyze_content.return_value = {
        "similarity_score": 0.85,
        "is_match": True,
        "confidence": "high",
        "features_matched": ["face", "watermark"],
        "analysis_details": {
            "face_similarity": 0.9,
            "image_hash_similarity": 0.8,
            "metadata_match": True
        }
    }
    matcher.add_reference_content.return_value = True
    matcher.remove_reference_content.return_value = True
    return matcher


@pytest.fixture
def mock_face_recognition():
    """Mock face recognition service."""
    service = AsyncMock()
    service.encode_face.return_value = [0.1, 0.2, 0.3]  # Mock encoding
    service.compare_faces.return_value = {"similarity": 0.85, "is_match": True}
    service.detect_faces.return_value = [{"bbox": [10, 10, 100, 100], "confidence": 0.9}]
    return service


@pytest.fixture
def mock_image_processor():
    """Mock image processing service."""
    processor = AsyncMock()
    processor.generate_hash.return_value = "abc123def456"
    processor.compare_hashes.return_value = {"similarity": 0.9, "is_similar": True}
    processor.extract_metadata.return_value = {"width": 1920, "height": 1080, "format": "JPEG"}
    return processor


# External service mocks
@pytest.fixture
def mock_stripe_service():
    """Mock Stripe service."""
    service = AsyncMock(spec=StripeService)
    service.create_customer.return_value = {"id": "cus_test123", "email": "test@example.com"}
    service.create_subscription.return_value = {"id": "sub_test123", "status": "active"}
    service.cancel_subscription.return_value = {"id": "sub_test123", "status": "canceled"}
    service.create_payment_intent.return_value = {"id": "pi_test123", "status": "succeeded"}
    return service


@pytest.fixture
def mock_email_service():
    """Mock email service."""
    service = AsyncMock()
    service.send_email.return_value = {"message_id": "test123", "status": "sent"}
    service.send_dmca_notice.return_value = {"message_id": "dmca123", "status": "sent"}
    service.send_notification.return_value = {"message_id": "notif123", "status": "sent"}
    return service


@pytest.fixture
def mock_social_media_service():
    """Mock social media monitoring service."""
    service = AsyncMock(spec=SocialMediaMonitoringService)
    service.start_monitoring.return_value = "job_id_123"
    service.get_monitoring_results.return_value = {
        "impersonations_found": 2,
        "accounts_flagged": ["fake_account1", "fake_account2"],
        "confidence_scores": [0.85, 0.92]
    }
    return service


@pytest.fixture
def mock_dmca_processor():
    """Mock DMCA takedown processor."""
    processor = AsyncMock(spec=TakedownProcessor)
    processor.process_takedown.return_value = {
        "takedown_id": "td_123",
        "status": "submitted",
        "notices_sent": 3,
        "hosting_providers": ["provider1.com", "provider2.com"]
    }
    processor.generate_notice.return_value = {
        "notice_html": "<html>DMCA Notice</html>",
        "notice_text": "DMCA Notice Text"
    }
    return processor


# Test data factories
@pytest.fixture
def content_data_factory():
    """Factory for creating test content data."""
    def _create_content_data(**kwargs):
        default_data = {
            "title": fake.sentence(),
            "description": fake.text(),
            "content_type": fake.random_element(["image", "video", "text"]),
            "url": fake.url(),
            "creator_id": str(uuid.uuid4()),
            "tags": [fake.word() for _ in range(3)],
            "metadata": {
                "resolution": "1920x1080",
                "format": "MP4",
                "duration": 120
            }
        }
        default_data.update(kwargs)
        return default_data
    return _create_content_data


@pytest.fixture
def dmca_request_factory():
    """Factory for creating DMCA request data."""
    def _create_dmca_request(**kwargs):
        default_data = {
            "infringing_url": fake.url(),
            "original_work_title": fake.sentence(),
            "copyright_owner": fake.name(),
            "contact_email": fake.email(),
            "infringement_description": fake.text(),
            "good_faith_statement": True,
            "accuracy_statement": True,
            "signature": fake.name(),
            "date_created": datetime.utcnow(),
        }
        default_data.update(kwargs)
        return default_data
    return _create_dmca_request


@pytest.fixture
def user_profile_factory():
    """Factory for creating user profile data."""
    def _create_profile(**kwargs):
        default_data = {
            "stage_name": fake.user_name(),
            "real_name": fake.name(),
            "bio": fake.text(max_nb_chars=200),
            "social_media_accounts": {
                "instagram": f"@{fake.user_name()}",
                "twitter": f"@{fake.user_name()}",
                "onlyfans": f"{fake.user_name()}"
            },
            "content_categories": ["photos", "videos"],
            "monitoring_keywords": [fake.word() for _ in range(5)],
            "protection_level": "premium"
        }
        default_data.update(kwargs)
        return default_data
    return _create_profile


# File handling fixtures
@pytest.fixture
def temp_image_file():
    """Create a temporary image file for testing."""
    from PIL import Image
    import io
    
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return {
        "filename": "test_image.jpg",
        "content": img_bytes.getvalue(),
        "content_type": "image/jpeg"
    }


@pytest.fixture
def temp_video_file():
    """Create a temporary video file for testing."""
    # In a real implementation, you'd create actual video data
    # For testing, we'll use placeholder data
    return {
        "filename": "test_video.mp4",
        "content": b"fake video content",
        "content_type": "video/mp4"
    }


# Performance testing fixtures
@pytest.fixture
def performance_config():
    """Configuration for performance tests."""
    return {
        "max_response_time": 2.0,  # seconds
        "max_memory_usage": 500,  # MB
        "concurrent_requests": 10,
        "test_duration": 30,  # seconds
    }


# Database seeding fixtures
@pytest.fixture
async def seed_test_data(db_session):
    """Seed the database with test data."""
    from app.models.user import User
    from app.models.profile import Profile
    
    # Create test users
    users = []
    for i in range(5):
        user = User(
            email=f"user{i}@test.com",
            username=f"testuser{i}",
            full_name=f"Test User {i}",
            hashed_password=get_password_hash("TestPassword123!"),
            is_active=True,
        )
        users.append(user)
        db_session.add(user)
    
    await db_session.commit()
    
    # Create test profiles
    profiles = []
    for i, user in enumerate(users):
        await db_session.refresh(user)
        profile = Profile(
            user_id=user.id,
            stage_name=f"Creator{i}",
            bio=f"Test creator {i} bio",
            monitoring_enabled=True,
        )
        profiles.append(profile)
        db_session.add(profile)
    
    await db_session.commit()
    
    return {"users": users, "profiles": profiles}


# Integration test helpers
@pytest.fixture
def integration_test_config():
    """Configuration for integration tests."""
    return {
        "test_timeout": 30,
        "retry_attempts": 3,
        "wait_between_retries": 1,
        "external_services_enabled": False,
    }


# WebSocket testing fixtures
@pytest.fixture
async def websocket_client():
    """Create a WebSocket test client."""
    from fastapi.testclient import TestClient
    
    with TestClient(app) as client:
        yield client


# Cache and Redis mocks
@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = True
    redis_mock.exists.return_value = False
    redis_mock.ping.return_value = True
    return redis_mock


# Security testing fixtures
@pytest.fixture
def security_test_payloads():
    """Common security test payloads."""
    return {
        "sql_injection": [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "1'; DELETE FROM users WHERE '1'='1'; --"
        ],
        "xss": [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//",
        ],
        "command_injection": [
            "; cat /etc/passwd",
            "| whoami",
            "&& ls -la",
            "$(cat /etc/passwd)"
        ]
    }


# API versioning fixtures
@pytest.fixture
def api_versions():
    """Test different API versions."""
    return ["v1", "v2"]


# Cleanup fixtures
@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Cleanup after each test."""
    yield
    # Cleanup logic here if needed
    pass