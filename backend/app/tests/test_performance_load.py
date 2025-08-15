"""
Performance and load testing suite for the Content Protection Platform.
Tests system performance under various load conditions and identifies bottlenecks.
"""

import pytest
import asyncio
import time
import psutil
import os
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, AsyncMock
import numpy as np
from statistics import mean, median

from fastapi.testclient import TestClient
from httpx import AsyncClient
import aiohttp

from app.main import app
from app.services.ai.content_matcher import ContentMatcher
from app.services.scanning.web_crawler import WebCrawler
from app.services.dmca.takedown_processor import TakedownProcessor


@pytest.mark.performance
@pytest.mark.asyncio
class TestAPIPerformance:
    """Test API endpoint performance under load."""

    @pytest.fixture
    def performance_client(self):
        """Create test client for performance testing."""
        return TestClient(app)

    @pytest.fixture
    def auth_token(self, test_user):
        """Create auth token for performance tests."""
        from app.core.security import create_access_token
        return create_access_token(subject=test_user.id)

    async def test_dashboard_api_performance(self, performance_client, auth_token):
        """Test dashboard API performance under concurrent load."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Baseline single request
        start_time = time.time()
        response = performance_client.get("/api/v1/dashboard/stats", headers=headers)
        baseline_time = time.time() - start_time
        
        assert response.status_code == 200
        assert baseline_time < 1.0  # Should respond within 1 second
        
        # Concurrent load test
        concurrent_requests = 50
        response_times = []
        
        async def make_request(session: aiohttp.ClientSession, url: str):
            start = time.time()
            async with session.get(url, headers=headers) as response:
                await response.json()
                return time.time() - start
        
        async with aiohttp.ClientSession() as session:
            tasks = [
                make_request(session, "http://localhost:8000/api/v1/dashboard/stats")
                for _ in range(concurrent_requests)
            ]
            response_times = await asyncio.gather(*tasks)
        
        # Performance assertions
        avg_response_time = mean(response_times)
        median_response_time = median(response_times)
        max_response_time = max(response_times)
        
        assert avg_response_time < 2.0  # Average under 2 seconds
        assert median_response_time < 1.5  # Median under 1.5 seconds
        assert max_response_time < 5.0  # No request over 5 seconds
        
        # Performance regression check
        assert avg_response_time < baseline_time * 3  # No more than 3x slower under load

    async def test_api_throughput_limits(self, performance_client, auth_token):
        """Test API throughput and identify limits."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test increasing load levels
        load_levels = [10, 25, 50, 100, 200]
        throughput_results = {}
        
        for concurrent_users in load_levels:
            start_time = time.time()
            
            async def make_requests(session: aiohttp.ClientSession):
                async with session.get(
                    "http://localhost:8000/api/v1/dashboard/stats",
                    headers=headers
                ) as response:
                    return response.status
            
            async with aiohttp.ClientSession() as session:
                tasks = [make_requests(session) for _ in range(concurrent_users)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            successful_requests = sum(1 for r in results if r == 200)
            requests_per_second = successful_requests / total_time
            
            throughput_results[concurrent_users] = {
                'rps': requests_per_second,
                'success_rate': successful_requests / concurrent_users,
                'total_time': total_time
            }
        
        # Verify throughput scaling
        assert throughput_results[10]['success_rate'] >= 0.95
        assert throughput_results[50]['success_rate'] >= 0.90
        assert throughput_results[100]['rps'] > throughput_results[10]['rps']

    async def test_memory_usage_under_load(self, performance_client, auth_token):
        """Test memory usage during high load."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        process = psutil.Process(os.getpid())
        
        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Sustained load
        duration = 60  # seconds
        requests_per_second = 10
        
        start_time = time.time()
        memory_samples = []
        
        async def sustained_load():
            while time.time() - start_time < duration:
                response = performance_client.get("/api/v1/dashboard/stats", headers=headers)
                assert response.status_code == 200
                
                # Sample memory every 5 seconds
                if len(memory_samples) == 0 or time.time() - memory_samples[-1]['time'] > 5:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_samples.append({
                        'time': time.time(),
                        'memory': current_memory
                    })
                
                await asyncio.sleep(1 / requests_per_second)
        
        await sustained_load()
        
        # Memory leak detection
        final_memory = memory_samples[-1]['memory']
        memory_growth = final_memory - baseline_memory
        
        # Should not grow more than 100MB during test
        assert memory_growth < 100
        
        # Check for linear growth (potential memory leak)
        if len(memory_samples) > 2:
            times = [s['time'] - start_time for s in memory_samples]
            memories = [s['memory'] for s in memory_samples]
            
            # Simple linear regression to detect memory leaks
            correlation = np.corrcoef(times, memories)[0, 1]
            assert abs(correlation) < 0.8  # Strong correlation indicates potential leak

    async def test_database_connection_pool_performance(self, db_session):
        """Test database connection pool under concurrent load."""
        
        async def db_operation():
            """Simulate database operation."""
            from sqlalchemy import text
            start_time = time.time()
            
            result = await db_session.execute(text("SELECT COUNT(*) FROM users"))
            await db_session.commit()
            
            return time.time() - start_time
        
        # Test with increasing concurrency
        concurrency_levels = [5, 10, 20, 50]
        
        for concurrency in concurrency_levels:
            start_time = time.time()
            
            tasks = [db_operation() for _ in range(concurrency)]
            operation_times = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            avg_operation_time = mean(operation_times)
            
            # Performance assertions
            assert avg_operation_time < 1.0  # Each operation under 1 second
            assert total_time < 10.0  # Total test under 10 seconds
            
            # Connection pool efficiency
            expected_time = avg_operation_time  # If pool is efficient
            efficiency = expected_time / total_time
            assert efficiency > 0.1  # At least 10% efficiency

    async def test_file_upload_performance(self, performance_client, auth_token):
        """Test file upload performance with various file sizes."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test different file sizes
        file_sizes = [
            (1024, "1KB"),
            (1024 * 100, "100KB"),
            (1024 * 1024, "1MB"),
            (1024 * 1024 * 5, "5MB"),
        ]
        
        upload_results = {}
        
        for size, label in file_sizes:
            # Create test file
            test_file_content = b"X" * size
            
            files = {"file": ("test_file.jpg", test_file_content, "image/jpeg")}
            data = {"profile_id": 1}
            
            start_time = time.time()
            response = performance_client.post(
                "/api/v1/ai/analyze-content",
                files=files,
                data=data,
                headers=headers
            )
            upload_time = time.time() - start_time
            
            upload_results[label] = {
                'time': upload_time,
                'speed_mbps': (size / 1024 / 1024) / upload_time if upload_time > 0 else 0,
                'status': response.status_code
            }
        
        # Performance expectations
        assert upload_results["1KB"]["time"] < 0.5
        assert upload_results["100KB"]["time"] < 1.0
        assert upload_results["1MB"]["time"] < 5.0
        assert upload_results["5MB"]["time"] < 15.0
        
        # All uploads should succeed
        for result in upload_results.values():
            assert result["status"] in [200, 202]


@pytest.mark.performance
@pytest.mark.asyncio
class TestServicePerformance:
    """Test individual service performance."""

    async def test_content_matcher_performance(self):
        """Test AI content matching performance."""
        content_matcher = ContentMatcher()
        
        # Mock AI operations for consistent testing
        with patch.object(content_matcher, '_generate_image_hash') as mock_hash:
            with patch.object(content_matcher, '_compare_image_hashes') as mock_compare:
                with patch('face_recognition.face_encodings') as mock_face:
                    
                    mock_hash.return_value = "test_hash"
                    mock_compare.return_value = {"similarity": 0.8, "is_match": True}
                    mock_face.return_value = [np.random.random(128)]
                    
                    # Single analysis baseline
                    test_content = b"fake image data" * 1000  # 1KB
                    
                    start_time = time.time()
                    result = await content_matcher.analyze_content(
                        content_data=test_content,
                        content_type="image",
                        reference_id="test_ref"
                    )
                    single_time = time.time() - start_time
                    
                    assert result is not None
                    assert single_time < 2.0  # Single analysis under 2 seconds
                    
                    # Batch analysis performance
                    batch_size = 10
                    content_batch = [
                        {"id": f"batch_{i}", "data": test_content, "type": "image"}
                        for i in range(batch_size)
                    ]
                    
                    start_time = time.time()
                    batch_results = await content_matcher.batch_analyze_content(
                        content_batch,
                        reference_id="test_ref"
                    )
                    batch_time = time.time() - start_time
                    
                    assert len(batch_results) == batch_size
                    assert batch_time < single_time * batch_size * 0.8  # Batch efficiency

    async def test_web_crawler_performance(self):
        """Test web crawler performance under load."""
        crawler = WebCrawler()
        
        # Mock HTTP requests for consistent testing
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text.return_value = "<html><body>Test content</body></html>"
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Single URL crawl
            start_time = time.time()
            result = await crawler.crawl_url("https://example.com/test")
            single_time = time.time() - start_time
            
            assert result is not None
            assert single_time < 5.0  # Single crawl under 5 seconds
            
            # Batch crawl performance
            urls = [f"https://example{i}.com/test" for i in range(20)]
            
            start_time = time.time()
            results = await crawler.batch_crawl_urls(urls, max_concurrent=5)
            batch_time = time.time() - start_time
            
            assert len(results) == 20
            assert batch_time < 30.0  # Batch crawl under 30 seconds
            
            # Concurrency efficiency
            expected_sequential_time = single_time * len(urls)
            efficiency = expected_sequential_time / batch_time
            assert efficiency > 2.0  # At least 2x faster than sequential

    async def test_takedown_processor_performance(self):
        """Test DMCA takedown processing performance."""
        processor = TakedownProcessor()
        
        # Mock external services
        with patch.object(processor, '_send_takedown_notice') as mock_send:
            with patch.object(processor, '_generate_dmca_notice') as mock_generate:
                
                mock_generate.return_value = {
                    "html_content": "<html>Notice</html>",
                    "text_content": "Notice text",
                    "notice_id": "test_123"
                }
                mock_send.return_value = {
                    "success": True,
                    "message_id": "msg_123"
                }
                
                # Single takedown processing
                from app.schemas.takedown import TakedownCreate
                
                takedown_data = TakedownCreate(
                    profile_id=1,
                    infringing_url="https://example.com/stolen",
                    original_work_title="Test Content",
                    copyright_owner="Test Owner",
                    contact_email="test@example.com",
                    infringement_description="Test description",
                    good_faith_statement=True,
                    accuracy_statement=True,
                    signature="Test Signature"
                )
                
                start_time = time.time()
                result = await processor.process_takedown(takedown_data)
                single_time = time.time() - start_time
                
                assert result is not None
                assert single_time < 3.0  # Single takedown under 3 seconds
                
                # Batch processing performance
                batch_requests = [takedown_data for _ in range(10)]
                
                start_time = time.time()
                batch_results = await processor.batch_process_takedowns(batch_requests)
                batch_time = time.time() - start_time
                
                assert len(batch_results) == 10
                assert batch_time < 20.0  # Batch processing under 20 seconds


@pytest.mark.performance
@pytest.mark.stress
class TestStressScenarios:
    """Stress testing under extreme conditions."""

    async def test_high_concurrency_mixed_workload(self, performance_client, auth_token):
        """Test system under high concurrency with mixed workload."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Define mixed workload
        workload_types = [
            {"endpoint": "/api/v1/dashboard/stats", "weight": 0.4},
            {"endpoint": "/api/v1/profiles", "weight": 0.3},
            {"endpoint": "/api/v1/infringements", "weight": 0.2},
            {"endpoint": "/api/v1/takedowns", "weight": 0.1},
        ]
        
        # Stress test parameters
        total_requests = 1000
        concurrent_users = 100
        duration = 300  # 5 minutes
        
        results = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "errors": []
        }
        
        async def stress_worker():
            """Single stress test worker."""
            session_start = time.time()
            
            async with aiohttp.ClientSession() as session:
                while time.time() - session_start < duration:
                    # Select random endpoint based on weight
                    import random
                    endpoint = random.choices(
                        [w["endpoint"] for w in workload_types],
                        weights=[w["weight"] for w in workload_types]
                    )[0]
                    
                    try:
                        request_start = time.time()
                        async with session.get(
                            f"http://localhost:8000{endpoint}",
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as response:
                            response_time = time.time() - request_start
                            
                            results["total_requests"] += 1
                            results["response_times"].append(response_time)
                            
                            if response.status == 200:
                                results["successful_requests"] += 1
                            else:
                                results["failed_requests"] += 1
                                
                    except Exception as e:
                        results["failed_requests"] += 1
                        results["errors"].append(str(e))
                    
                    await asyncio.sleep(0.1)  # Brief pause between requests
        
        # Run stress test
        start_time = time.time()
        
        tasks = [stress_worker() for _ in range(concurrent_users)]
        await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Performance analysis
        success_rate = results["successful_requests"] / results["total_requests"]
        avg_response_time = mean(results["response_times"]) if results["response_times"] else 0
        requests_per_second = results["total_requests"] / total_time
        
        # Stress test assertions
        assert success_rate > 0.95  # 95% success rate under stress
        assert avg_response_time < 5.0  # Average response time under 5 seconds
        assert requests_per_second > 50  # At least 50 RPS
        
        # Error analysis
        error_rate = results["failed_requests"] / results["total_requests"]
        assert error_rate < 0.05  # Less than 5% error rate

    async def test_memory_stress_test(self, performance_client, auth_token):
        """Test system under memory stress conditions."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        process = psutil.Process(os.getpid())
        
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create memory-intensive workload
        large_payloads = []
        
        for i in range(100):
            # Create large file upload
            large_content = b"X" * (1024 * 1024)  # 1MB per request
            files = {"file": (f"large_file_{i}.jpg", large_content, "image/jpeg")}
            data = {"profile_id": 1}
            
            response = performance_client.post(
                "/api/v1/ai/analyze-content",
                files=files,
                data=data,
                headers=headers
            )
            
            large_payloads.append(response.status_code)
            
            # Monitor memory every 10 requests
            if i % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                
                # Memory should not grow excessively
                assert memory_increase < 500  # Less than 500MB increase
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory
        
        # Memory should stabilize after stress
        await asyncio.sleep(30)  # Wait for garbage collection
        
        stabilized_memory = process.memory_info().rss / 1024 / 1024
        assert stabilized_memory < final_memory + 50  # Memory should not continue growing

    async def test_database_stress_test(self, db_session):
        """Test database under stress conditions."""
        
        # Heavy query workload
        async def heavy_db_operations():
            operations = []
            
            for i in range(100):
                # Complex queries that stress the database
                from sqlalchemy import text
                
                start_time = time.time()
                
                # Simulate complex analytics query
                await db_session.execute(text("""
                    SELECT COUNT(*), AVG(confidence_score)
                    FROM infringements 
                    WHERE created_at > NOW() - INTERVAL '30 days'
                    GROUP BY platform
                """))
                
                # Simulate heavy write operation
                await db_session.execute(text("""
                    INSERT INTO infringements 
                    (profile_id, url, title, description, platform, confidence_score, status)
                    VALUES (1, :url, :title, :description, 'test', 0.8, 'detected')
                """), {
                    "url": f"https://stress-test-{i}.com",
                    "title": f"Stress Test {i}",
                    "description": f"Stress test description {i}"
                })
                
                await db_session.commit()
                
                operation_time = time.time() - start_time
                operations.append(operation_time)
                
                # Brief pause to prevent overwhelming
                await asyncio.sleep(0.01)
            
            return operations
        
        # Run concurrent database stress
        concurrent_workers = 5
        
        start_time = time.time()
        
        tasks = [heavy_db_operations() for _ in range(concurrent_workers)]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Flatten results
        all_operations = [op for worker_ops in results for op in worker_ops]
        
        # Performance assertions
        avg_operation_time = mean(all_operations)
        max_operation_time = max(all_operations)
        
        assert avg_operation_time < 1.0  # Average operation under 1 second
        assert max_operation_time < 5.0  # No operation over 5 seconds
        assert total_time < 60.0  # Total stress test under 1 minute


@pytest.mark.performance
@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Establish performance benchmarks for regression testing."""

    def test_api_endpoint_benchmarks(self, performance_client, auth_token):
        """Establish performance benchmarks for all API endpoints."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Define benchmark expectations
        benchmarks = {
            "/api/v1/dashboard/stats": {"max_time": 1.0, "target_time": 0.5},
            "/api/v1/profiles": {"max_time": 2.0, "target_time": 1.0},
            "/api/v1/infringements": {"max_time": 3.0, "target_time": 1.5},
            "/api/v1/takedowns": {"max_time": 2.0, "target_time": 1.0},
            "/api/v1/billing/subscription": {"max_time": 1.5, "target_time": 0.8},
        }
        
        results = {}
        
        for endpoint, benchmark in benchmarks.items():
            # Warm up
            performance_client.get(endpoint, headers=headers)
            
            # Benchmark measurement
            times = []
            for _ in range(10):  # 10 samples
                start_time = time.time()
                response = performance_client.get(endpoint, headers=headers)
                response_time = time.time() - start_time
                
                assert response.status_code == 200
                times.append(response_time)
            
            avg_time = mean(times)
            min_time = min(times)
            max_time = max(times)
            
            results[endpoint] = {
                "avg_time": avg_time,
                "min_time": min_time,
                "max_time": max_time,
                "benchmark_max": benchmark["max_time"],
                "benchmark_target": benchmark["target_time"],
            }
            
            # Benchmark assertions
            assert max_time < benchmark["max_time"], f"{endpoint} exceeded max time benchmark"
            
            # Warning for target time (not failure)
            if avg_time > benchmark["target_time"]:
                print(f"WARNING: {endpoint} exceeded target time: {avg_time:.3f}s > {benchmark['target_time']}s")
        
        # Save benchmark results for trend analysis
        import json
        with open("performance_benchmarks.json", "w") as f:
            json.dump(results, f, indent=2)

    async def test_scalability_benchmark(self, performance_client, auth_token):
        """Test system scalability characteristics."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test increasing load levels
        load_levels = [1, 5, 10, 25, 50, 100]
        scalability_results = {}
        
        for concurrent_users in load_levels:
            response_times = []
            
            async def benchmark_request():
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "http://localhost:8000/api/v1/dashboard/stats",
                        headers=headers
                    ) as response:
                        await response.json()
                        return time.time() - start_time
            
            # Run concurrent requests
            tasks = [benchmark_request() for _ in range(concurrent_users)]
            response_times = await asyncio.gather(*tasks)
            
            scalability_results[concurrent_users] = {
                "avg_response_time": mean(response_times),
                "median_response_time": median(response_times),
                "max_response_time": max(response_times),
                "throughput": concurrent_users / mean(response_times),
            }
        
        # Analyze scalability characteristics
        single_user_time = scalability_results[1]["avg_response_time"]
        
        for users, metrics in scalability_results.items():
            if users > 1:
                # Response time should not degrade more than 3x under load
                degradation_factor = metrics["avg_response_time"] / single_user_time
                assert degradation_factor < 3.0, f"Performance degraded {degradation_factor:.1f}x at {users} users"
                
                # Throughput should generally increase with more users (up to a point)
                if users <= 25:
                    assert metrics["throughput"] > scalability_results[1]["throughput"]