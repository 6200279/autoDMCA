"""
Pytest configuration and fixtures for AutoDMCA tests.
"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import numpy as np
from PIL import Image

from scanning.config import ScannerConfig, ScannerSettings, PiracySiteConfig
from scanning.processors.face_recognition_processor import FaceRecognitionProcessor
from scanning.processors.image_hash_processor import ImageHashProcessor
from scanning.processors.content_matcher import ContentMatcher
from scanning.crawlers.piracy_crawler import InfringingContent, PiracySiteCrawler
from scanning.queue.dmca_queue import DMCAQueue, DMCARequest


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def test_settings():
    """Create test scanner settings."""
    return ScannerSettings(
        database_url="sqlite:///:memory:",
        redis_url="redis://localhost:6379/15",  # Test DB
        face_recognition_tolerance=0.6,
        similarity_threshold=0.85,
        requests_per_minute=30,
        concurrent_requests=5,
        temp_storage_path="/tmp/test_autodmca",
        log_level="DEBUG"
    )


@pytest.fixture
def test_config(test_settings, temp_dir):
    """Create test scanner configuration."""
    config = ScannerConfig(settings=test_settings)
    
    # Add test piracy sites
    config.piracy_sites = [
        PiracySiteConfig(
            name="test_site_1",
            base_url="https://test-site-1.example.com",
            search_patterns=["/search?q={username}"],
            content_selectors={
                "title": ".post-title",
                "content": ".post-content"
            }
        ),
        PiracySiteConfig(
            name="test_site_2", 
            base_url="https://test-site-2.example.com",
            search_patterns=["/search/{username}"],
            content_selectors={
                "title": ".item-title",
                "images": "img.item-image"
            },
            requires_proxy=True
        )
    ]
    
    # Set test search terms
    config.search_keywords = [
        "test_user",
        "test_user leaked",
        "test_content"
    ]
    
    return config


@pytest.fixture
def sample_image():
    """Create a sample test image."""
    # Create a simple test image
    image = Image.new('RGB', (100, 100), color='blue')
    return np.array(image)


@pytest.fixture
def sample_face_image():
    """Create a sample image with a simple face-like pattern."""
    # Create a simple face-like pattern for testing
    image = Image.new('RGB', (200, 200), color='white')
    
    # Draw simple face features (this won't work with real face recognition,
    # but serves as test data)
    import PIL.ImageDraw as ImageDraw
    draw = ImageDraw.Draw(image)
    
    # Face outline
    draw.ellipse([50, 50, 150, 150], fill='lightpink')
    # Eyes
    draw.ellipse([70, 80, 80, 90], fill='black')
    draw.ellipse([120, 80, 130, 90], fill='black')
    # Mouth
    draw.arc([80, 110, 120, 130], 0, 180, fill='black')
    
    return np.array(image)


@pytest.fixture
def sample_infringing_content():
    """Create sample infringing content for testing."""
    return [
        InfringingContent(
            title="Test User Leaked Photos",
            url="https://example-leak-site.com/post/123",
            site_name="example-leak-site.com",
            content_type="image",
            description="Some leaked content description",
            thumbnail_url="https://example-leak-site.com/thumb/123.jpg",
            download_urls=["https://example-leak-site.com/img/123.jpg"],
            uploader="anonymous",
            matched_keywords=["test_user", "leaked"]
        ),
        InfringingContent(
            title="Free Premium Content",
            url="https://another-site.com/free/456",
            site_name="another-site.com",
            content_type="video",
            description="Free access to premium content",
            thumbnail_url="https://another-site.com/thumb/456.jpg",
            download_urls=["https://another-site.com/video/456.mp4"],
            matched_keywords=["test_user", "premium"]
        )
    ]


@pytest.fixture
async def mock_face_processor():
    """Create mock face recognition processor."""
    processor = AsyncMock(spec=FaceRecognitionProcessor)
    processor.initialize.return_value = None
    processor.close.return_value = None
    processor.add_person.return_value = 3  # Mock 3 face encodings added
    processor.process_image.return_value = MagicMock(
        has_matches=True,
        best_match=MagicMock(
            person_id="test_person",
            confidence=0.85,
            distance=0.15,
            is_match=True
        )
    )
    return processor


@pytest.fixture
async def mock_image_processor():
    """Create mock image hash processor.""" 
    processor = AsyncMock(spec=ImageHashProcessor)
    processor.initialize.return_value = None
    processor.close.return_value = None
    processor.add_reference_images.return_value = 4  # Mock 4 hashes added
    processor.find_matches.return_value = [
        MagicMock(
            similarity_score=0.92,
            is_similar=True,
            reference_hash=MagicMock(person_id="test_person")
        )
    ]
    return processor


@pytest.fixture
async def mock_dmca_queue():
    """Create mock DMCA queue."""
    queue = AsyncMock(spec=DMCAQueue)
    queue.initialize.return_value = None
    queue.close.return_value = None
    queue.enqueue_request.return_value = True
    queue.get_queue_status.return_value = {
        'pending': 5,
        'processing': 2, 
        'completed': 10,
        'failed': 1
    }
    return queue


@pytest.fixture
def mock_redis():
    """Create mock Redis connection."""
    redis_mock = AsyncMock()
    redis_mock.ping.return_value = True
    redis_mock.set.return_value = True
    redis_mock.get.return_value = None
    redis_mock.hset.return_value = True
    redis_mock.hget.return_value = None
    redis_mock.zadd.return_value = True
    redis_mock.zrevrange.return_value = []
    return redis_mock


@pytest.fixture
def mock_http_session():
    """Create mock HTTP session for web requests."""
    session = AsyncMock()
    
    # Mock successful response
    response_mock = AsyncMock()
    response_mock.status = 200
    response_mock.text.return_value = "<html><body>Test content</body></html>"
    response_mock.read.return_value = b"test image data"
    response_mock.headers = {'content-type': 'text/html'}
    
    session.get.return_value.__aenter__.return_value = response_mock
    session.get.return_value.__aexit__.return_value = None
    
    return session


@pytest.fixture
def sample_dmca_request():
    """Create sample DMCA request for testing."""
    return DMCARequest(
        person_id="test_person",
        infringing_url="https://example.com/leaked-content",
        hosting_provider="example.com",
        contact_email="abuse@example.com",
        original_work_title="Original Content by Test Person",
        copyright_owner="Test Person",
        infringement_description="Unauthorized use of copyrighted material"
    )


@pytest.fixture
def mock_search_results():
    """Create mock search engine results."""
    from scanning.crawlers.search_engine_api import SearchResult
    
    return [
        SearchResult(
            title="Test User Content Found",
            url="https://leak-site.com/test-user-content",
            snippet="Some description of leaked content",
            source_engine="google",
            domain="leak-site.com"
        ),
        SearchResult(
            title="Free Test User Photos",
            url="https://another-site.com/test-user-photos", 
            snippet="Download free photos",
            source_engine="bing",
            domain="another-site.com"
        )
    ]


# Async test helpers
class AsyncContextManager:
    """Helper for async context manager mocking."""
    
    def __init__(self, return_value=None):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value or self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


def make_async_mock(return_value=None, side_effect=None):
    """Create async mock function."""
    mock = AsyncMock(return_value=return_value, side_effect=side_effect)
    return mock