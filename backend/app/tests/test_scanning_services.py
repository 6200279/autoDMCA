"""
Comprehensive tests for scanning services including web crawling,
search engine scanning, and multi-profile optimization.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import json
import requests
from typing import List, Dict, Any

from app.services.scanning.web_crawler import WebCrawler, CrawlResult
from app.services.scanning.search_engines import SearchEngineScanner, SearchResult
from app.services.scanning.scheduler import ScanScheduler, ScanJob
from app.services.scanning.multi_profile_optimizer import MultiProfileOptimizer
from app.models.scanning import ScanRequest, ScanStatus


@pytest.mark.unit
@pytest.mark.scanning
class TestWebCrawler:
    """Test web crawler functionality."""

    @pytest.fixture
    def web_crawler(self):
        """Create web crawler instance."""
        return WebCrawler()

    @pytest.fixture
    def mock_requests_session(self):
        """Mock requests session."""
        session = AsyncMock()
        session.get.return_value.status_code = 200
        session.get.return_value.text = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <img src="/test-image.jpg" alt="test image">
                <p>Some content with username @testuser</p>
                <a href="/profile/testuser">Profile Link</a>
            </body>
        </html>
        """
        return session

    @pytest.mark.asyncio
    async def test_crawl_url_success(self, web_crawler, mock_requests_session):
        """Test successful URL crawling."""
        with patch.object(web_crawler, '_get_session', return_value=mock_requests_session):
            result = await web_crawler.crawl_url("https://example.com/test")
            
            assert result is not None
            assert result.url == "https://example.com/test"
            assert result.status_code == 200
            assert "Test Page" in result.content
            assert result.images is not None
            assert result.links is not None

    @pytest.mark.asyncio
    async def test_crawl_url_with_images(self, web_crawler, mock_requests_session):
        """Test URL crawling with image extraction."""
        with patch.object(web_crawler, '_get_session', return_value=mock_requests_session):
            result = await web_crawler.crawl_url("https://example.com/test")
            
            # Should extract images from HTML
            assert len(result.images) > 0
            assert any("/test-image.jpg" in img for img in result.images)

    @pytest.mark.asyncio
    async def test_crawl_url_with_profile_detection(self, web_crawler, mock_requests_session):
        """Test URL crawling with profile mention detection."""
        profile_data = {
            "username": "testuser",
            "keywords": ["testuser", "profile"]
        }
        
        with patch.object(web_crawler, '_get_session', return_value=mock_requests_session):
            result = await web_crawler.crawl_url(
                "https://example.com/test",
                profile_data=profile_data
            )
            
            assert result.profile_mentions > 0
            assert "testuser" in result.metadata.get("keywords_found", [])

    @pytest.mark.asyncio
    async def test_crawl_url_timeout(self, web_crawler):
        """Test URL crawling with timeout."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = asyncio.TimeoutError()
            
            result = await web_crawler.crawl_url("https://slow-site.com")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_crawl_url_http_error(self, web_crawler):
        """Test URL crawling with HTTP error."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await web_crawler.crawl_url("https://notfound.com")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_batch_crawl_urls(self, web_crawler, mock_requests_session):
        """Test batch URL crawling."""
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3"
        ]
        
        with patch.object(web_crawler, '_get_session', return_value=mock_requests_session):
            results = await web_crawler.batch_crawl_urls(urls)
            
            assert len(results) == 3
            assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_crawl_with_rate_limiting(self, web_crawler, mock_requests_session):
        """Test crawling with rate limiting."""
        with patch.object(web_crawler, '_get_session', return_value=mock_requests_session):
            with patch('asyncio.sleep') as mock_sleep:
                await web_crawler.crawl_url("https://example.com", rate_limit=1.0)
                
                # Should have called sleep for rate limiting
                mock_sleep.assert_called()

    def test_extract_images_from_html(self, web_crawler):
        """Test image extraction from HTML."""
        html = """
        <html>
            <body>
                <img src="image1.jpg" alt="test">
                <img src="/absolute/image2.png">
                <img src="https://example.com/image3.gif">
            </body>
        </html>
        """
        
        images = web_crawler._extract_images(html, "https://example.com")
        
        assert len(images) == 3
        assert "https://example.com/image1.jpg" in images
        assert "https://example.com/absolute/image2.png" in images
        assert "https://example.com/image3.gif" in images

    def test_extract_links_from_html(self, web_crawler):
        """Test link extraction from HTML."""
        html = """
        <html>
            <body>
                <a href="page1.html">Link 1</a>
                <a href="/absolute/page2.html">Link 2</a>
                <a href="https://external.com/page3.html">Link 3</a>
            </body>
        </html>
        """
        
        links = web_crawler._extract_links(html, "https://example.com")
        
        assert len(links) == 3
        assert "https://example.com/page1.html" in links
        assert "https://example.com/absolute/page2.html" in links
        assert "https://external.com/page3.html" in links


@pytest.mark.unit
@pytest.mark.scanning
class TestSearchEngineScanner:
    """Test search engine scanning functionality."""

    @pytest.fixture
    def search_scanner(self):
        """Create search engine scanner instance."""
        return SearchEngineScanner()

    @pytest.fixture
    def mock_google_response(self):
        """Mock Google search API response."""
        return {
            "items": [
                {
                    "title": "Test Result 1",
                    "link": "https://example.com/result1",
                    "snippet": "Content containing testuser",
                    "pagemap": {
                        "cse_image": [{"src": "https://example.com/image1.jpg"}]
                    }
                },
                {
                    "title": "Test Result 2", 
                    "link": "https://example.com/result2",
                    "snippet": "Another relevant result"
                }
            ]
        }

    @pytest.fixture
    def mock_bing_response(self):
        """Mock Bing search API response."""
        return {
            "webPages": {
                "value": [
                    {
                        "name": "Bing Result 1",
                        "url": "https://example.com/bing1",
                        "snippet": "Bing search result"
                    }
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_google_search_success(self, search_scanner, mock_google_response):
        """Test successful Google search."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_google_response
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            results = await search_scanner.search_google("testuser photos")
            
            assert len(results) == 2
            assert results[0].title == "Test Result 1"
            assert results[0].url == "https://example.com/result1"
            assert "testuser" in results[0].snippet

    @pytest.mark.asyncio
    async def test_bing_search_success(self, search_scanner, mock_bing_response):
        """Test successful Bing search."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_bing_response
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            results = await search_scanner.search_bing("testuser content")
            
            assert len(results) == 1
            assert results[0].title == "Bing Result 1"
            assert results[0].url == "https://example.com/bing1"

    @pytest.mark.asyncio
    async def test_search_with_profile_targeting(self, search_scanner, mock_google_response):
        """Test search with profile-specific targeting."""
        profile_data = {
            "username": "testuser",
            "stage_name": "TestCreator",
            "keywords": ["photos", "content"]
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_google_response
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            results = await search_scanner.search_for_profile(profile_data)
            
            assert len(results) > 0
            # Should have used profile data to construct search queries
            mock_get.assert_called()

    @pytest.mark.asyncio
    async def test_search_api_rate_limiting(self, search_scanner):
        """Test search API rate limiting."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 429  # Rate limited
            mock_get.return_value.__aenter__.return_value = mock_response
            
            with patch('asyncio.sleep') as mock_sleep:
                results = await search_scanner.search_google("test query")
                
                # Should handle rate limiting
                assert results == []
                mock_sleep.assert_called()

    @pytest.mark.asyncio
    async def test_search_api_error_handling(self, search_scanner):
        """Test search API error handling."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("API Error")
            
            results = await search_scanner.search_google("test query")
            
            assert results == []

    def test_build_search_queries_for_profile(self, search_scanner):
        """Test search query building for profile."""
        profile_data = {
            "username": "testuser",
            "stage_name": "TestCreator", 
            "keywords": ["photos", "videos"],
            "social_media_accounts": {
                "instagram": "@testuser",
                "twitter": "@testcreator"
            }
        }
        
        queries = search_scanner._build_search_queries(profile_data)
        
        assert len(queries) > 0
        assert any("testuser" in query for query in queries)
        assert any("TestCreator" in query for query in queries)
        assert any("photos" in query for query in queries)

    def test_filter_relevant_results(self, search_scanner):
        """Test filtering of relevant search results."""
        results = [
            SearchResult(
                title="Relevant Result",
                url="https://example.com/relevant",
                snippet="Contains testuser content",
                source="google"
            ),
            SearchResult(
                title="Irrelevant Result",
                url="https://example.com/irrelevant", 
                snippet="Random unrelated content",
                source="google"
            )
        ]
        
        profile_data = {"username": "testuser"}
        filtered = search_scanner._filter_relevant_results(results, profile_data)
        
        assert len(filtered) == 1
        assert filtered[0].title == "Relevant Result"


@pytest.mark.unit
@pytest.mark.scanning
class TestScanScheduler:
    """Test scan scheduling functionality."""

    @pytest.fixture
    def scan_scheduler(self):
        """Create scan scheduler instance."""
        return ScanScheduler()

    @pytest.fixture
    def sample_scan_job(self):
        """Create sample scan job."""
        return ScanJob(
            id="job_123",
            profile_id=1,
            scan_type="web_search",
            parameters={"keywords": ["testuser"]},
            scheduled_at=datetime.utcnow(),
            status=ScanStatus.PENDING
        )

    @pytest.mark.asyncio
    async def test_schedule_scan_job(self, scan_scheduler, sample_scan_job):
        """Test scheduling a scan job."""
        with patch.object(scan_scheduler, '_store_job') as mock_store:
            mock_store.return_value = True
            
            result = await scan_scheduler.schedule_job(sample_scan_job)
            
            assert result is True
            mock_store.assert_called_once_with(sample_scan_job)

    @pytest.mark.asyncio
    async def test_execute_scan_job(self, scan_scheduler, sample_scan_job):
        """Test executing a scan job."""
        with patch.object(scan_scheduler, '_execute_web_search') as mock_execute:
            mock_execute.return_value = {"results": ["test"]}
            
            result = await scan_scheduler.execute_job(sample_scan_job)
            
            assert result is not None
            assert "results" in result
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pending_jobs(self, scan_scheduler):
        """Test getting pending scan jobs."""
        with patch.object(scan_scheduler, '_get_jobs_by_status') as mock_get:
            mock_get.return_value = [ScanJob(
                id="job_1",
                profile_id=1,
                scan_type="web_search",
                status=ScanStatus.PENDING
            )]
            
            jobs = await scan_scheduler.get_pending_jobs()
            
            assert len(jobs) == 1
            assert jobs[0].status == ScanStatus.PENDING

    @pytest.mark.asyncio
    async def test_update_job_status(self, scan_scheduler):
        """Test updating job status."""
        with patch.object(scan_scheduler, '_update_job_status') as mock_update:
            mock_update.return_value = True
            
            result = await scan_scheduler.update_job_status(
                "job_123", 
                ScanStatus.COMPLETED
            )
            
            assert result is True
            mock_update.assert_called_once_with("job_123", ScanStatus.COMPLETED)

    @pytest.mark.asyncio
    async def test_schedule_recurring_scan(self, scan_scheduler):
        """Test scheduling recurring scans."""
        profile_id = 1
        scan_config = {
            "frequency": "daily",
            "scan_types": ["web_search", "social_media"],
            "parameters": {"depth": 2}
        }
        
        with patch.object(scan_scheduler, '_create_recurring_jobs') as mock_create:
            mock_create.return_value = ["job_1", "job_2"]
            
            job_ids = await scan_scheduler.schedule_recurring_scan(
                profile_id, 
                scan_config
            )
            
            assert len(job_ids) == 2
            mock_create.assert_called_once()

    def test_calculate_next_run_time(self, scan_scheduler):
        """Test calculation of next run time."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        # Test daily frequency
        next_time = scan_scheduler._calculate_next_run_time(base_time, "daily")
        expected = base_time + timedelta(days=1)
        assert next_time == expected
        
        # Test weekly frequency
        next_time = scan_scheduler._calculate_next_run_time(base_time, "weekly")
        expected = base_time + timedelta(weeks=1)
        assert next_time == expected


@pytest.mark.unit
@pytest.mark.scanning
class TestMultiProfileOptimizer:
    """Test multi-profile scanning optimization."""

    @pytest.fixture
    def optimizer(self):
        """Create multi-profile optimizer instance."""
        return MultiProfileOptimizer()

    @pytest.fixture
    def sample_profiles(self):
        """Create sample profiles for testing."""
        return [
            {
                "id": 1,
                "username": "creator1",
                "keywords": ["photos", "model"],
                "priority": "high"
            },
            {
                "id": 2,
                "username": "creator2", 
                "keywords": ["videos", "content"],
                "priority": "medium"
            },
            {
                "id": 3,
                "username": "creator3",
                "keywords": ["art", "digital"],
                "priority": "low"
            }
        ]

    @pytest.mark.asyncio
    async def test_optimize_scan_batch(self, optimizer, sample_profiles):
        """Test optimization of scan batch."""
        scan_requests = [
            {"profile_id": 1, "scan_type": "web_search"},
            {"profile_id": 2, "scan_type": "web_search"},
            {"profile_id": 3, "scan_type": "social_media"}
        ]
        
        with patch.object(optimizer, '_group_by_similarity') as mock_group:
            mock_group.return_value = [
                [scan_requests[0], scan_requests[1]],  # Similar profiles
                [scan_requests[2]]  # Different profile
            ]
            
            optimized = await optimizer.optimize_batch(
                scan_requests, 
                sample_profiles
            )
            
            assert len(optimized) == 2  # Two batches
            assert len(optimized[0]) == 2  # First batch has 2 scans
            assert len(optimized[1]) == 1  # Second batch has 1 scan

    @pytest.mark.asyncio
    async def test_deduplicate_search_queries(self, optimizer):
        """Test deduplication of search queries."""
        queries = [
            "creator1 photos",
            "creator2 photos", 
            "creator1 photos",  # Duplicate
            "creator1 videos"
        ]
        
        deduplicated = optimizer._deduplicate_queries(queries)
        
        assert len(deduplicated) == 3
        assert "creator1 photos" in deduplicated
        assert deduplicated.count("creator1 photos") == 1

    @pytest.mark.asyncio
    async def test_priority_based_scheduling(self, optimizer, sample_profiles):
        """Test priority-based job scheduling."""
        scan_jobs = [
            {"profile_id": 3, "priority": "low"},
            {"profile_id": 1, "priority": "high"},
            {"profile_id": 2, "priority": "medium"}
        ]
        
        sorted_jobs = optimizer._sort_by_priority(scan_jobs)
        
        # Should be sorted: high, medium, low
        assert sorted_jobs[0]["priority"] == "high"
        assert sorted_jobs[1]["priority"] == "medium"
        assert sorted_jobs[2]["priority"] == "low"

    def test_calculate_scan_similarity(self, optimizer):
        """Test calculation of scan similarity between profiles."""
        profile1 = {
            "username": "creator1",
            "keywords": ["photos", "model", "fashion"]
        }
        profile2 = {
            "username": "creator2", 
            "keywords": ["photos", "fashion", "style"]
        }
        profile3 = {
            "username": "creator3",
            "keywords": ["videos", "gaming"]
        }
        
        similarity_1_2 = optimizer._calculate_similarity(profile1, profile2)
        similarity_1_3 = optimizer._calculate_similarity(profile1, profile3)
        
        # profile1 and profile2 should be more similar (shared keywords)
        assert similarity_1_2 > similarity_1_3

    @pytest.mark.asyncio
    async def test_resource_constraint_optimization(self, optimizer):
        """Test optimization with resource constraints."""
        scan_jobs = [
            {"profile_id": i, "estimated_cost": 10} for i in range(20)
        ]
        
        constraints = {
            "max_concurrent_scans": 5,
            "max_daily_cost": 50
        }
        
        optimized = await optimizer.optimize_with_constraints(
            scan_jobs,
            constraints
        )
        
        # Should respect max concurrent scans
        assert len(optimized) <= constraints["max_concurrent_scans"]
        
        # Should respect cost constraints
        total_cost = sum(job["estimated_cost"] for job in optimized)
        assert total_cost <= constraints["max_daily_cost"]


@pytest.mark.integration
@pytest.mark.scanning
class TestScanningIntegration:
    """Integration tests for scanning services."""

    @pytest.mark.asyncio
    async def test_end_to_end_profile_scan(self, db_session):
        """Test complete profile scanning workflow."""
        # This would test the integration of all scanning components
        profile_data = {
            "id": 1,
            "username": "testcreator",
            "keywords": ["photos", "content"],
            "monitoring_enabled": True
        }
        
        web_crawler = WebCrawler()
        search_scanner = SearchEngineScanner()
        scheduler = ScanScheduler()
        
        # Mock external services
        with patch.object(search_scanner, 'search_google') as mock_search:
            mock_search.return_value = [
                SearchResult(
                    title="Test Result",
                    url="https://example.com/test",
                    snippet="testcreator content",
                    source="google"
                )
            ]
            
            with patch.object(web_crawler, 'crawl_url') as mock_crawl:
                mock_crawl.return_value = CrawlResult(
                    url="https://example.com/test",
                    status_code=200,
                    content="<html>testcreator photos</html>",
                    images=["https://example.com/photo.jpg"],
                    profile_mentions=1
                )
                
                # Execute scan workflow
                search_results = await search_scanner.search_for_profile(profile_data)
                assert len(search_results) > 0
                
                crawl_results = []
                for result in search_results:
                    crawl_result = await web_crawler.crawl_url(result.url)
                    if crawl_result:
                        crawl_results.append(crawl_result)
                
                assert len(crawl_results) > 0
                assert crawl_results[0].profile_mentions > 0


@pytest.mark.performance
@pytest.mark.scanning
class TestScanningPerformance:
    """Performance tests for scanning services."""

    @pytest.mark.asyncio
    async def test_concurrent_crawling_performance(self):
        """Test performance of concurrent web crawling."""
        import time
        
        web_crawler = WebCrawler()
        urls = [f"https://example.com/page{i}" for i in range(50)]
        
        with patch.object(web_crawler, 'crawl_url') as mock_crawl:
            mock_crawl.return_value = CrawlResult(
                url="test",
                status_code=200,
                content="test",
                images=[],
                profile_mentions=0
            )
            
            start_time = time.time()
            results = await web_crawler.batch_crawl_urls(urls, max_concurrent=10)
            end_time = time.time()
            
            assert len(results) == 50
            assert (end_time - start_time) < 30  # Should complete within 30 seconds

    @pytest.mark.asyncio
    async def test_search_api_quota_management(self):
        """Test search API quota management."""
        search_scanner = SearchEngineScanner()
        
        # Test many search requests
        queries = [f"test query {i}" for i in range(100)]
        
        with patch.object(search_scanner, 'search_google') as mock_search:
            mock_search.return_value = []
            
            # Should implement quota management
            for query in queries:
                await search_scanner.search_google(query)
            
            # Should not exceed API limits
            assert mock_search.call_count <= 100