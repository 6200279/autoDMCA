"""
Production Load Testing with Locust
Simulates realistic user behavior and validates performance under load
"""
import json
import random
import time
from typing import Dict, Any
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
import logging

logger = logging.getLogger(__name__)


class ContentProtectionUser(HttpUser):
    """
    Simulates a typical Content Protection Platform user
    Performs realistic user actions with weighted probabilities
    """
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Initialize user session"""
        # Login and get auth token
        self.login()
        
        # Cache some data for realistic behavior
        self.profile_ids = []
        self.infringement_ids = []
        self.takedown_ids = []
        
    def login(self):
        """Authenticate user and store token"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "test_user",
            "password": "test_password"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            logger.error(f"Login failed: {response.status_code}")
            self.headers = {}
    
    @task(30)
    def view_dashboard(self):
        """View dashboard - most common action"""
        with self.client.get(
            "/api/v1/dashboard/stats",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                
                # Validate response time
                if response.elapsed.total_seconds() > 2:
                    response.failure(f"Dashboard too slow: {response.elapsed.total_seconds():.2f}s")
            else:
                response.failure(f"Dashboard failed: {response.status_code}")
    
    @task(20)
    def list_profiles(self):
        """List content profiles"""
        with self.client.get(
            "/api/v1/profiles",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                data = response.json()
                
                # Store profile IDs for other tasks
                if data.get("profiles"):
                    self.profile_ids = [p["id"] for p in data["profiles"][:10]]
            else:
                response.failure(f"Profile list failed: {response.status_code}")
    
    @task(15)
    def view_infringements(self):
        """View detected infringements"""
        params = {
            "limit": 20,
            "offset": 0,
            "status": "detected"
        }
        
        with self.client.get(
            "/api/v1/infringements",
            params=params,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                data = response.json()
                
                # Store infringement IDs
                if data.get("infringements"):
                    self.infringement_ids = [i["id"] for i in data["infringements"][:10]]
            else:
                response.failure(f"Infringement list failed: {response.status_code}")
    
    @task(10)
    def analyze_content(self):
        """Submit content for AI analysis"""
        if not self.profile_ids:
            return
        
        # Simulate image upload
        profile_id = random.choice(self.profile_ids)
        
        # Create small test image data
        image_data = b"fake_image_data" * 100  # ~1.5KB
        
        files = {"file": ("test_image.jpg", image_data, "image/jpeg")}
        data = {"profile_id": profile_id}
        
        with self.client.post(
            "/api/v1/ai/analyze-content",
            files=files,
            data=data,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
                
                # Check AI inference time
                if response.elapsed.total_seconds() > 2:
                    response.failure(f"AI analysis too slow: {response.elapsed.total_seconds():.2f}s")
            else:
                response.failure(f"AI analysis failed: {response.status_code}")
    
    @task(8)
    def create_takedown(self):
        """Create DMCA takedown notice"""
        if not self.infringement_ids:
            return
        
        infringement_id = random.choice(self.infringement_ids)
        
        takedown_data = {
            "infringement_id": infringement_id,
            "recipient_email": "infringer@example.com",
            "good_faith_statement": True,
            "accuracy_statement": True,
            "signature": "Test User"
        }
        
        with self.client.post(
            "/api/v1/takedowns",
            json=takedown_data,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
                data = response.json()
                
                if data.get("id"):
                    self.takedown_ids.append(data["id"])
            else:
                response.failure(f"Takedown creation failed: {response.status_code}")
    
    @task(5)
    def view_profile_details(self):
        """View detailed profile information"""
        if not self.profile_ids:
            return
        
        profile_id = random.choice(self.profile_ids)
        
        with self.client.get(
            f"/api/v1/profiles/{profile_id}",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Profile details failed: {response.status_code}")
    
    @task(5)
    def search_content(self):
        """Search for content"""
        search_terms = ["copyright", "infringement", "dmca", "content", "protection"]
        query = random.choice(search_terms)
        
        params = {"q": query, "limit": 10}
        
        with self.client.get(
            "/api/v1/search",
            params=params,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Search failed: {response.status_code}")
    
    @task(3)
    def view_analytics(self):
        """View analytics dashboard"""
        with self.client.get(
            "/api/v1/analytics/overview",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Analytics failed: {response.status_code}")
    
    @task(2)
    def export_report(self):
        """Export performance report"""
        params = {
            "format": "json",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31"
        }
        
        with self.client.get(
            "/api/v1/reports/export",
            params=params,
            headers=self.headers,
            catch_response=True,
            stream=True
        ) as response:
            if response.status_code == 200:
                response.success()
                
                # Validate export time
                if response.elapsed.total_seconds() > 5:
                    response.failure(f"Report export too slow: {response.elapsed.total_seconds():.2f}s")
            else:
                response.failure(f"Report export failed: {response.status_code}")


class AdminUser(HttpUser):
    """
    Simulates an admin user with more intensive operations
    """
    
    wait_time = between(2, 5)
    weight = 1  # 10% of users are admins (if weight is 10 for regular users)
    
    def on_start(self):
        """Initialize admin session"""
        self.login_admin()
    
    def login_admin(self):
        """Authenticate as admin"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "admin_user",
            "password": "admin_password"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}
    
    @task(10)
    def admin_dashboard(self):
        """View admin dashboard with all metrics"""
        with self.client.get(
            "/api/v1/admin/dashboard",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Admin dashboard failed: {response.status_code}")
    
    @task(5)
    def bulk_operations(self):
        """Perform bulk operations"""
        operation_data = {
            "action": "approve",
            "infringement_ids": list(range(1, 51))  # 50 items
        }
        
        with self.client.post(
            "/api/v1/admin/bulk-operations",
            json=operation_data,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Bulk operation failed: {response.status_code}")
    
    @task(3)
    def system_metrics(self):
        """Get system performance metrics"""
        with self.client.get(
            "/api/v1/admin/metrics",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                
                # Validate metrics
                data = response.json()
                if data.get("cpu_percent", 0) > 80:
                    logger.warning(f"High CPU usage: {data['cpu_percent']}%")
                if data.get("memory_percent", 0) > 85:
                    logger.warning(f"High memory usage: {data['memory_percent']}%")
            else:
                response.failure(f"System metrics failed: {response.status_code}")


class MobileUser(HttpUser):
    """
    Simulates mobile app user with different behavior patterns
    """
    
    wait_time = between(3, 8)  # Mobile users interact less frequently
    weight = 3  # 30% of users are on mobile
    
    def on_start(self):
        """Initialize mobile session"""
        self.login_mobile()
        self.headers["User-Agent"] = "ContentProtection-Mobile/1.0"
    
    def login_mobile(self):
        """Mobile authentication"""
        response = self.client.post("/api/v1/auth/mobile/login", json={
            "username": "mobile_user",
            "password": "mobile_password",
            "device_id": f"device_{random.randint(1000, 9999)}"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "X-Mobile-Version": "1.0"
            }
        else:
            self.headers = {"X-Mobile-Version": "1.0"}
    
    @task(40)
    def mobile_dashboard(self):
        """Simplified mobile dashboard"""
        with self.client.get(
            "/api/v1/mobile/dashboard",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                
                # Mobile response time should be faster
                if response.elapsed.total_seconds() > 1:
                    response.failure(f"Mobile dashboard slow: {response.elapsed.total_seconds():.2f}s")
            else:
                response.failure(f"Mobile dashboard failed: {response.status_code}")
    
    @task(30)
    def mobile_notifications(self):
        """Check push notifications"""
        with self.client.get(
            "/api/v1/mobile/notifications",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Notifications failed: {response.status_code}")
    
    @task(20)
    def quick_scan(self):
        """Quick content scan from mobile camera"""
        # Smaller image for mobile
        image_data = b"mobile_image" * 50  # ~600 bytes
        
        files = {"file": ("mobile_photo.jpg", image_data, "image/jpeg")}
        
        with self.client.post(
            "/api/v1/mobile/quick-scan",
            files=files,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
                
                # Mobile scan should be very fast
                if response.elapsed.total_seconds() > 3:
                    response.failure(f"Mobile scan slow: {response.elapsed.total_seconds():.2f}s")
            else:
                response.failure(f"Mobile scan failed: {response.status_code}")


# Performance statistics collection
stats_history = []

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, 
                context, exception, start_time, url, **kwargs):
    """Collect detailed performance metrics"""
    if exception:
        return
    
    # Collect stats for SLA monitoring
    stats_history.append({
        "timestamp": time.time(),
        "endpoint": name,
        "response_time_ms": response_time,
        "status_code": response.status_code if response else 0
    })
    
    # Keep only last 1000 entries
    if len(stats_history) > 1000:
        stats_history.pop(0)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate performance report at test end"""
    if not stats_history:
        return
    
    # Calculate SLA compliance
    total_requests = len(stats_history)
    slow_requests = sum(1 for s in stats_history if s["response_time_ms"] > 2000)
    failed_requests = sum(1 for s in stats_history if s["status_code"] >= 500)
    
    sla_compliance = {
        "total_requests": total_requests,
        "slow_requests": slow_requests,
        "failed_requests": failed_requests,
        "response_time_compliance": (total_requests - slow_requests) / total_requests * 100,
        "availability": (total_requests - failed_requests) / total_requests * 100
    }
    
    # Save report
    with open("locust_sla_report.json", "w") as f:
        json.dump({
            "sla_compliance": sla_compliance,
            "test_duration": environment.stats.last_request_timestamp - environment.stats.start_time,
            "peak_users": environment.runner.user_count if environment.runner else 0,
            "targets": {
                "response_time_ms": 2000,
                "availability_percent": 99.9,
                "concurrent_users": 1000
            }
        }, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("LOAD TEST PERFORMANCE SUMMARY")
    print("="*60)
    print(f"Total Requests: {total_requests}")
    print(f"Response Time SLA Compliance: {sla_compliance['response_time_compliance']:.1f}%")
    print(f"Availability: {sla_compliance['availability']:.2f}%")
    
    if sla_compliance['response_time_compliance'] >= 95 and sla_compliance['availability'] >= 99.9:
        print("✅ SLA TARGETS MET")
    else:
        print("❌ SLA TARGETS NOT MET")


# Custom shape for load testing (gradual ramp-up)
def custom_shape(settings):
    """
    Custom load shape for realistic testing
    Gradually ramps up to peak load, sustains, then ramps down
    """
    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 1},      # Warm-up
        {"duration": 300, "users": 100, "spawn_rate": 2},    # Ramp-up
        {"duration": 600, "users": 500, "spawn_rate": 5},    # Increase
        {"duration": 1200, "users": 1000, "spawn_rate": 10}, # Peak load
        {"duration": 600, "users": 1000, "spawn_rate": 0},   # Sustain
        {"duration": 300, "users": 100, "spawn_rate": -5},   # Ramp-down
        {"duration": 60, "users": 0, "spawn_rate": -2},      # Cool-down
    ]
    
    run_time = 0
    for stage in stages:
        run_time += stage["duration"]
        if settings["run_time"] < run_time:
            return stage["users"], stage["spawn_rate"]
    
    return None