"""
Comprehensive Load Testing Suite
Load testing for AI inference, API endpoints, and system performance validation
"""
import asyncio
import aiohttp
import time
import statistics
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor
import io
from PIL import Image
import numpy as np

from app.core.config import settings
from app.services.monitoring.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


class TestType(str, Enum):
    LOAD = "load"
    STRESS = "stress"
    SPIKE = "spike"
    ENDURANCE = "endurance"
    CAPACITY = "capacity"


class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class LoadTestConfig:
    """Load test configuration"""
    test_name: str
    test_type: TestType
    target_url: str
    concurrent_users: int
    duration_seconds: int
    ramp_up_seconds: int = 0
    ramp_down_seconds: int = 0
    think_time_ms: int = 1000
    timeout_seconds: int = 30
    success_criteria: Dict[str, float] = field(default_factory=dict)
    test_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Individual test request result"""
    timestamp: datetime
    response_time_ms: float
    status_code: int
    success: bool
    error: Optional[str] = None
    response_size_bytes: int = 0
    request_id: str = ""


@dataclass
class LoadTestReport:
    """Comprehensive load test report"""
    test_config: LoadTestConfig
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime]
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    requests_per_second: float
    error_rate_percent: float
    throughput_mb_per_second: float
    success_criteria_met: bool
    errors: Dict[str, int] = field(default_factory=dict)
    response_time_histogram: List[Tuple[float, int]] = field(default_factory=list)


class TestDataGenerator:
    """Generate test data for various scenarios"""
    
    @staticmethod
    def generate_user_profile() -> Dict[str, Any]:
        """Generate random user profile for testing"""
        usernames = [
            "test_creator_001", "demo_user_123", "content_creator_456",
            "model_test_789", "creator_demo_999", "test_profile_abc"
        ]
        
        platforms = ["onlyfans", "patreon", "fansly", "justforfans"]
        
        return {
            "username": random.choice(usernames),
            "platform": random.choice(platforms),
            "keywords": [f"keyword_{i}" for i in range(random.randint(3, 8))],
            "scan_images": True,
            "scan_videos": random.choice([True, False]),
            "notification_settings": {
                "email_alerts": True,
                "sms_alerts": False
            }
        }
    
    @staticmethod
    def generate_test_image(width: int = 224, height: int = 224) -> bytes:
        """Generate test image data"""
        # Create random RGB image
        image_array = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        image = Image.fromarray(image_array)
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    
    @staticmethod
    def generate_scan_urls(count: int = 10) -> List[str]:
        """Generate test URLs for scanning"""
        domains = [
            "example-leak-site.com",
            "test-content-site.org",
            "demo-platform.net",
            "sample-social-media.com"
        ]
        
        paths = [
            "/search", "/profile", "/content", "/media",
            "/user", "/gallery", "/posts", "/images"
        ]
        
        urls = []
        for _ in range(count):
            domain = random.choice(domains)
            path = random.choice(paths)
            query = f"?q=test_user_{random.randint(1, 100)}"
            urls.append(f"https://{domain}{path}{query}")
        
        return urls


class LoadTestRunner:
    """
    Advanced load testing system for AI and API performance validation
    
    Features:
    - Multiple test types (load, stress, spike, endurance)
    - Real-time metrics collection
    - AI inference load testing
    - Database performance testing
    - SLA validation
    - Automated reporting
    - Performance regression detection
    """
    
    def __init__(self):
        self.active_tests: Dict[str, LoadTestReport] = {}
        self.test_history: List[LoadTestReport] = []
        self.data_generator = TestDataGenerator()
        
        # Test execution control
        self.max_concurrent_tests = 3
        self.test_executor = ThreadPoolExecutor(max_workers=10)
        
        # Default success criteria
        self.default_criteria = {
            'max_avg_response_time_ms': 2000,
            'max_error_rate_percent': 5.0,
            'min_requests_per_second': 10.0,
            'max_p95_response_time_ms': 3000
        }
        
        logger.info("Load test runner initialized")
    
    async def run_api_load_test(self, config: LoadTestConfig) -> LoadTestReport:
        """Run comprehensive API load test"""
        
        test_id = f"{config.test_name}_{int(time.time())}"
        
        # Initialize test report
        report = LoadTestReport(
            test_config=config,
            status=TestStatus.RUNNING,
            start_time=datetime.utcnow(),
            end_time=None,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            avg_response_time_ms=0.0,
            min_response_time_ms=float('inf'),
            max_response_time_ms=0.0,
            p50_response_time_ms=0.0,
            p95_response_time_ms=0.0,
            p99_response_time_ms=0.0,
            requests_per_second=0.0,
            error_rate_percent=0.0,
            throughput_mb_per_second=0.0,
            success_criteria_met=False
        )
        
        self.active_tests[test_id] = report
        
        try:
            # Create HTTP session with optimizations
            connector = aiohttp.TCPConnector(
                limit=config.concurrent_users * 2,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            
            timeout = aiohttp.ClientTimeout(total=config.timeout_seconds)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # Run the test
                results = await self._execute_load_test(session, config, report)
                
                # Analyze results
                await self._analyze_test_results(results, report)
                
                # Check success criteria
                report.success_criteria_met = self._check_success_criteria(report, config.success_criteria)
                
                report.status = TestStatus.COMPLETED
                report.end_time = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"Load test {test_id} failed: {e}")
            report.status = TestStatus.FAILED
            report.end_time = datetime.utcnow()
        
        finally:
            # Move to history
            if test_id in self.active_tests:
                del self.active_tests[test_id]
            self.test_history.append(report)
            
            # Keep only recent history
            if len(self.test_history) > 50:
                self.test_history = self.test_history[-30:]
        
        return report
    
    async def _execute_load_test(
        self,
        session: aiohttp.ClientSession,
        config: LoadTestConfig,
        report: LoadTestReport
    ) -> List[TestResult]:
        """Execute the actual load test"""
        
        results = []
        tasks = []
        
        # Calculate test parameters
        test_duration = config.duration_seconds
        concurrent_users = config.concurrent_users
        
        # Ramp-up phase
        if config.ramp_up_seconds > 0:
            logger.info(f"Ramping up to {concurrent_users} users over {config.ramp_up_seconds}s")
            await self._ramp_up_users(session, config, results)
        
        # Main test phase
        logger.info(f"Starting main load test: {concurrent_users} users for {test_duration}s")
        
        # Create user tasks
        for user_id in range(concurrent_users):
            task = asyncio.create_task(
                self._simulate_user(session, config, user_id, test_duration, results)
            )
            tasks.append(task)
        
        # Monitor progress
        start_time = time.time()
        while time.time() - start_time < test_duration:
            await asyncio.sleep(5)
            
            # Update real-time metrics
            current_results = list(results)  # Copy current results
            if current_results:
                await self._update_realtime_metrics(current_results, report)
            
            logger.info(f"Test progress: {len(current_results)} requests completed")
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Ramp-down phase
        if config.ramp_down_seconds > 0:
            logger.info(f"Ramping down over {config.ramp_down_seconds}s")
            await asyncio.sleep(config.ramp_down_seconds)
        
        return results
    
    async def _simulate_user(
        self,
        session: aiohttp.ClientSession,
        config: LoadTestConfig,
        user_id: int,
        duration: int,
        results: List[TestResult]
    ):
        """Simulate individual user behavior"""
        
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < duration:
            try:
                # Generate test request
                request_data = await self._generate_test_request(config, user_id)
                
                # Execute request
                result = await self._execute_test_request(
                    session, config, request_data, f"{user_id}_{request_count}"
                )
                
                results.append(result)
                request_count += 1
                
                # Think time
                if config.think_time_ms > 0:
                    await asyncio.sleep(config.think_time_ms / 1000)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"User {user_id} error: {e}")
                error_result = TestResult(
                    timestamp=datetime.utcnow(),
                    response_time_ms=0.0,
                    status_code=0,
                    success=False,
                    error=str(e),
                    request_id=f"{user_id}_{request_count}"
                )
                results.append(error_result)
    
    async def _generate_test_request(self, config: LoadTestConfig, user_id: int) -> Dict[str, Any]:
        """Generate test request data"""
        
        endpoint = config.target_url
        
        if "scan" in endpoint.lower():
            # Scanning endpoint test
            return {
                'method': 'POST',
                'url': endpoint,
                'json': {
                    'profile_data': self.data_generator.generate_user_profile(),
                    'max_urls': random.randint(10, 50),
                    'deep_scan': random.choice([True, False])
                }
            }
        
        elif "analyze" in endpoint.lower():
            # AI analysis endpoint test
            return {
                'method': 'POST',
                'url': endpoint,
                'data': {
                    'content_url': f"https://test-site.com/image_{user_id}_{random.randint(1, 1000)}.jpg",
                    'content_data': self.data_generator.generate_test_image(),
                    'profile_data': self.data_generator.generate_user_profile()
                }
            }
        
        elif "dmca" in endpoint.lower():
            # DMCA endpoint test
            return {
                'method': 'POST',
                'url': endpoint,
                'json': {
                    'infringing_url': f"https://leak-site.com/content_{random.randint(1, 10000)}",
                    'description': f"Test DMCA request {user_id}",
                    'profile_id': random.randint(1, 100)
                }
            }
        
        else:
            # Generic GET request
            return {
                'method': 'GET',
                'url': endpoint,
                'params': {'test_param': f'user_{user_id}'}
            }
    
    async def _execute_test_request(
        self,
        session: aiohttp.ClientSession,
        config: LoadTestConfig,
        request_data: Dict[str, Any],
        request_id: str
    ) -> TestResult:
        """Execute individual test request"""
        
        start_time = time.time()
        
        try:
            method = request_data.get('method', 'GET')
            url = request_data.get('url')
            
            if method == 'GET':
                async with session.get(url, params=request_data.get('params')) as response:
                    content = await response.read()
                    
            elif method == 'POST':
                if 'json' in request_data:
                    async with session.post(url, json=request_data['json']) as response:
                        content = await response.read()
                elif 'data' in request_data:
                    # For file uploads
                    data = aiohttp.FormData()
                    for key, value in request_data['data'].items():
                        if isinstance(value, bytes):
                            data.add_field(key, value, content_type='application/octet-stream')
                        else:
                            data.add_field(key, str(value))
                    
                    async with session.post(url, data=data) as response:
                        content = await response.read()
                else:
                    async with session.post(url) as response:
                        content = await response.read()
            
            response_time = (time.time() - start_time) * 1000
            success = 200 <= response.status < 400
            
            return TestResult(
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
                status_code=response.status,
                success=success,
                response_size_bytes=len(content),
                request_id=request_id
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            return TestResult(
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
                status_code=0,
                success=False,
                error=str(e),
                request_id=request_id
            )
    
    async def _ramp_up_users(
        self,
        session: aiohttp.ClientSession,
        config: LoadTestConfig,
        results: List[TestResult]
    ):
        """Gradually ramp up user load"""
        
        ramp_interval = config.ramp_up_seconds / config.concurrent_users
        
        for user_id in range(config.concurrent_users):
            # Start user simulation
            asyncio.create_task(
                self._simulate_user(session, config, user_id, config.duration_seconds, results)
            )
            
            # Wait before starting next user
            await asyncio.sleep(ramp_interval)
    
    async def _update_realtime_metrics(self, results: List[TestResult], report: LoadTestReport):
        """Update real-time test metrics"""
        
        if not results:
            return
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        response_times = [r.response_time_ms for r in results]
        
        report.total_requests = len(results)
        report.successful_requests = len(successful)
        report.failed_requests = len(failed)
        
        if response_times:
            report.avg_response_time_ms = statistics.mean(response_times)
            report.min_response_time_ms = min(response_times)
            report.max_response_time_ms = max(response_times)
            
            sorted_times = sorted(response_times)
            n = len(sorted_times)
            report.p50_response_time_ms = sorted_times[int(n * 0.5)]
            report.p95_response_time_ms = sorted_times[int(n * 0.95)]
            report.p99_response_time_ms = sorted_times[int(n * 0.99)]
        
        # Calculate RPS
        if results:
            time_span = (results[-1].timestamp - results[0].timestamp).total_seconds()
            if time_span > 0:
                report.requests_per_second = len(results) / time_span
        
        # Error rate
        report.error_rate_percent = (len(failed) / len(results)) * 100 if results else 0.0
    
    async def _analyze_test_results(self, results: List[TestResult], report: LoadTestReport):
        """Comprehensive analysis of test results"""
        
        if not results:
            return
        
        # Update final metrics
        await self._update_realtime_metrics(results, report)
        
        # Calculate throughput
        total_bytes = sum(r.response_size_bytes for r in results)
        time_span = (results[-1].timestamp - results[0].timestamp).total_seconds()
        if time_span > 0:
            report.throughput_mb_per_second = (total_bytes / 1024 / 1024) / time_span
        
        # Error analysis
        error_counts = {}
        for result in results:
            if not result.success and result.error:
                error_counts[result.error] = error_counts.get(result.error, 0) + 1
        
        report.errors = error_counts
        
        # Response time histogram
        response_times = [r.response_time_ms for r in results if r.success]
        if response_times:
            histogram = self._create_histogram(response_times)
            report.response_time_histogram = histogram
    
    def _create_histogram(self, values: List[float], bins: int = 20) -> List[Tuple[float, int]]:
        """Create histogram from response time values"""
        
        if not values:
            return []
        
        min_val = min(values)
        max_val = max(values)
        bin_width = (max_val - min_val) / bins
        
        histogram = []
        for i in range(bins):
            bin_start = min_val + i * bin_width
            bin_end = bin_start + bin_width
            
            count = sum(1 for v in values if bin_start <= v < bin_end)
            histogram.append((bin_end, count))
        
        return histogram
    
    def _check_success_criteria(
        self,
        report: LoadTestReport,
        custom_criteria: Dict[str, float]
    ) -> bool:
        """Check if test meets success criteria"""
        
        criteria = {**self.default_criteria, **custom_criteria}
        
        checks = [
            report.avg_response_time_ms <= criteria.get('max_avg_response_time_ms', float('inf')),
            report.error_rate_percent <= criteria.get('max_error_rate_percent', 100.0),
            report.requests_per_second >= criteria.get('min_requests_per_second', 0.0),
            report.p95_response_time_ms <= criteria.get('max_p95_response_time_ms', float('inf'))
        ]
        
        return all(checks)
    
    async def run_ai_inference_load_test(
        self,
        batch_sizes: List[int] = [1, 4, 8, 16],
        concurrent_requests: int = 10,
        duration_seconds: int = 300
    ) -> Dict[str, Any]:
        """Specialized load test for AI inference performance"""
        
        results = {}
        
        for batch_size in batch_sizes:
            logger.info(f"Testing AI inference with batch size {batch_size}")
            
            # Create test configuration
            config = LoadTestConfig(
                test_name=f"ai_inference_batch_{batch_size}",
                test_type=TestType.LOAD,
                target_url="/api/v1/ai/analyze-content",
                concurrent_users=concurrent_requests,
                duration_seconds=duration_seconds,
                think_time_ms=100,
                test_data={'batch_size': batch_size}
            )
            
            # Run test
            report = await self.run_api_load_test(config)
            
            results[f"batch_size_{batch_size}"] = {
                'avg_response_time_ms': report.avg_response_time_ms,
                'p95_response_time_ms': report.p95_response_time_ms,
                'requests_per_second': report.requests_per_second,
                'error_rate_percent': report.error_rate_percent,
                'success_criteria_met': report.success_criteria_met
            }
        
        # Find optimal batch size
        optimal_batch = min(
            results.keys(),
            key=lambda k: results[k]['avg_response_time_ms']
        )
        
        return {
            'batch_test_results': results,
            'optimal_batch_size': optimal_batch,
            'recommendation': f"Use batch size {optimal_batch.split('_')[-1]} for best performance"
        }
    
    async def run_stress_test(self, base_config: LoadTestConfig) -> LoadTestReport:
        """Run stress test with increasing load"""
        
        stress_config = LoadTestConfig(
            test_name=f"{base_config.test_name}_stress",
            test_type=TestType.STRESS,
            target_url=base_config.target_url,
            concurrent_users=base_config.concurrent_users * 3,  # 3x normal load
            duration_seconds=base_config.duration_seconds,
            ramp_up_seconds=60,  # Gradual ramp up
            success_criteria={
                'max_avg_response_time_ms': 5000,  # More lenient
                'max_error_rate_percent': 10.0,
                'min_requests_per_second': 5.0
            }
        )
        
        return await self.run_api_load_test(stress_config)
    
    async def run_endurance_test(self, base_config: LoadTestConfig) -> LoadTestReport:
        """Run endurance test for extended duration"""
        
        endurance_config = LoadTestConfig(
            test_name=f"{base_config.test_name}_endurance",
            test_type=TestType.ENDURANCE,
            target_url=base_config.target_url,
            concurrent_users=base_config.concurrent_users,
            duration_seconds=3600,  # 1 hour
            think_time_ms=2000,  # Slower pace
            success_criteria={
                'max_avg_response_time_ms': 3000,
                'max_error_rate_percent': 2.0,
                'min_requests_per_second': 8.0
            }
        )
        
        return await self.run_api_load_test(endurance_config)
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary of all test results"""
        
        if not self.test_history:
            return {'status': 'no_tests'}
        
        recent_tests = self.test_history[-10:]  # Last 10 tests
        
        avg_response_times = [t.avg_response_time_ms for t in recent_tests]
        success_rates = [(t.successful_requests / t.total_requests) * 100 for t in recent_tests if t.total_requests > 0]
        
        return {
            'total_tests_run': len(self.test_history),
            'active_tests': len(self.active_tests),
            'recent_avg_response_time_ms': statistics.mean(avg_response_times) if avg_response_times else 0,
            'recent_success_rate_percent': statistics.mean(success_rates) if success_rates else 0,
            'tests_passed': sum(1 for t in recent_tests if t.success_criteria_met),
            'tests_failed': sum(1 for t in recent_tests if not t.success_criteria_met),
            'last_test_time': recent_tests[-1].start_time.isoformat() if recent_tests else None
        }


# Global load test runner
load_test_runner = LoadTestRunner()