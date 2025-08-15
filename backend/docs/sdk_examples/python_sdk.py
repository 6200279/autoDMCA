"""
Content Protection Platform - Python SDK Examples
Comprehensive examples for integrating with the Content Protection API using Python
"""

import asyncio
import aiohttp
import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentProtectionSDK:
    """
    Comprehensive Python SDK for the Content Protection Platform API
    
    Features:
    - Automatic token refresh
    - Rate limiting handling
    - Async and sync methods
    - Comprehensive error handling
    - Webhook verification
    """
    
    def __init__(self, base_url: str = "https://api.contentprotection.ai"):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.session = requests.Session()
    
    def authenticate(self, email: str, password: str, remember_me: bool = True) -> Dict[str, Any]:
        """Authenticate and store tokens"""
        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login",
            json={
                "email": email,
                "password": password,
                "remember_me": remember_me
            }
        )
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        
        # Calculate expiration time with 5-minute buffer
        expires_in = data["expires_in"]
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
        
        logger.info("Authentication successful")
        return data
    
    def _refresh_token_if_needed(self):
        """Automatically refresh token if needed"""
        if (self.token_expires_at and 
            datetime.now() >= self.token_expires_at):
            
            if not self.refresh_token:
                raise Exception("No refresh token available. Please re-authenticate.")
            
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/refresh",
                json={"refresh_token": self.refresh_token}
            )
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            
            expires_in = data["expires_in"]
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
            
            logger.info("Token refreshed successfully")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        self._refresh_token_if_needed()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated API request with error handling"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('X-RateLimit-Retry-After', 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
        
        raise Exception("Max retries exceeded")


class ProfileManager:
    """Manage protected profiles"""
    
    def __init__(self, sdk: ContentProtectionSDK):
        self.sdk = sdk
    
    def create_profile(self, name: str, platform: str, username: str, 
                      keywords: List[str] = None) -> Dict[str, Any]:
        """Create a new protected profile"""
        data = {
            "name": name,
            "platform": platform,
            "username": username,
            "keywords": keywords or [],
            "monitoring_enabled": True
        }
        
        return self.sdk._make_request("POST", "/api/v1/profiles", json=data)
    
    def upload_reference_content(self, profile_id: int, image_urls: List[str]) -> Dict[str, Any]:
        """Upload reference content for AI signature generation"""
        return self.sdk._make_request(
            "POST",
            "/api/v1/scanning/profile/signatures",
            json={
                "profile_id": profile_id,
                "image_urls": image_urls[:10]  # Limit to 10 images
            }
        )
    
    def get_profile(self, profile_id: int) -> Dict[str, Any]:
        """Get profile details"""
        return self.sdk._make_request("GET", f"/api/v1/profiles/{profile_id}")
    
    def list_profiles(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """List all profiles"""
        params = {"limit": limit, "offset": offset}
        return self.sdk._make_request("GET", "/api/v1/profiles", params=params)
    
    def update_profile(self, profile_id: int, **updates) -> Dict[str, Any]:
        """Update profile settings"""
        return self.sdk._make_request("PUT", f"/api/v1/profiles/{profile_id}", json=updates)


class ScanningManager:
    """Manage content scanning operations"""
    
    def __init__(self, sdk: ContentProtectionSDK):
        self.sdk = sdk
    
    def trigger_manual_scan(self, profile_id: int) -> Dict[str, Any]:
        """Trigger a manual scan for unauthorized content"""
        return self.sdk._make_request(
            "POST",
            "/api/v1/scanning/scan/manual",
            params={"profile_id": profile_id}
        )
    
    def scan_specific_url(self, url: str, profile_id: int) -> Dict[str, Any]:
        """Scan a specific URL for content matches"""
        return self.sdk._make_request(
            "POST",
            "/api/v1/scanning/scan/url",
            params={"url": url, "profile_id": profile_id}
        )
    
    def get_scan_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a scanning job"""
        return self.sdk._make_request("GET", f"/api/v1/scanning/scan/status/{job_id}")
    
    def wait_for_scan_completion(self, job_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for scan to complete with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_scan_status(job_id)
            
            if status["status"] == "completed":
                logger.info(f"Scan {job_id} completed successfully")
                return status
            elif status["status"] == "failed":
                raise Exception(f"Scan {job_id} failed: {status.get('error')}")
            
            time.sleep(30)  # Check every 30 seconds
        
        raise TimeoutError(f"Scan {job_id} did not complete within {timeout} seconds")
    
    def get_scan_history(self, profile_id: int = None, limit: int = 50) -> Dict[str, Any]:
        """Get scanning history"""
        params = {"limit": limit}
        if profile_id:
            params["profile_id"] = profile_id
        
        return self.sdk._make_request("GET", "/api/v1/scanning/scan/history", params=params)
    
    def configure_scan_schedule(self, profile_id: int, frequency: str = "daily",
                               time: str = "02:00", platforms: List[str] = None) -> Dict[str, Any]:
        """Configure automated scanning schedule"""
        schedule_data = {
            "profile_id": profile_id,
            "schedule": {
                "frequency": frequency,
                "time": time,
                "platforms": platforms or ["google", "bing", "social_media"]
            }
        }
        
        return self.sdk._make_request("POST", "/api/v1/scanning/scan/schedule", json=schedule_data)


class InfringementManager:
    """Manage detected infringements"""
    
    def __init__(self, sdk: ContentProtectionSDK):
        self.sdk = sdk
    
    def list_infringements(self, profile_id: int = None, status: str = None,
                          confidence_threshold: float = 0.0, limit: int = 50) -> Dict[str, Any]:
        """List detected infringements with filters"""
        params = {"limit": limit}
        
        if profile_id:
            params["profile_id"] = profile_id
        if status:
            params["status"] = status
        if confidence_threshold > 0:
            params["min_confidence"] = confidence_threshold
        
        return self.sdk._make_request("GET", "/api/v1/infringements", params=params)
    
    def get_infringement(self, infringement_id: int) -> Dict[str, Any]:
        """Get detailed infringement information"""
        return self.sdk._make_request("GET", f"/api/v1/infringements/{infringement_id}")
    
    def update_infringement_status(self, infringement_id: int, status: str,
                                  notes: str = None) -> Dict[str, Any]:
        """Update infringement status (confirmed, false_positive, ignored)"""
        data = {"status": status}
        if notes:
            data["notes"] = notes
        
        return self.sdk._make_request("PUT", f"/api/v1/infringements/{infringement_id}", json=data)
    
    def bulk_process_infringements(self, infringement_ids: List[int],
                                  action: str, **kwargs) -> Dict[str, Any]:
        """Process multiple infringements at once"""
        data = {
            "infringement_ids": infringement_ids,
            "action": action,
            **kwargs
        }
        
        return self.sdk._make_request("POST", "/api/v1/infringements/bulk", json=data)


class TakedownManager:
    """Manage DMCA takedown requests"""
    
    def __init__(self, sdk: ContentProtectionSDK):
        self.sdk = sdk
    
    def submit_takedown(self, infringement_id: int, urgency: str = "normal",
                       additional_info: str = None, template_id: int = None) -> Dict[str, Any]:
        """Submit a DMCA takedown request"""
        data = {
            "infringement_id": infringement_id,
            "urgency": urgency
        }
        
        if additional_info:
            data["additional_info"] = additional_info
        if template_id:
            data["template_id"] = template_id
        
        return self.sdk._make_request("POST", "/api/v1/takedowns", json=data)
    
    def get_takedown_status(self, takedown_id: str) -> Dict[str, Any]:
        """Get takedown request status"""
        return self.sdk._make_request("GET", f"/api/v1/takedowns/{takedown_id}")
    
    def list_takedowns(self, status: str = None, platform: str = None,
                      limit: int = 50) -> Dict[str, Any]:
        """List takedown requests with filters"""
        params = {"limit": limit}
        
        if status:
            params["status"] = status
        if platform:
            params["platform"] = platform
        
        return self.sdk._make_request("GET", "/api/v1/takedowns", params=params)
    
    def cancel_takedown(self, takedown_id: str, reason: str) -> Dict[str, Any]:
        """Cancel a pending takedown request"""
        return self.sdk._make_request(
            "POST",
            f"/api/v1/takedowns/{takedown_id}/cancel",
            json={"reason": reason}
        )


class WebhookManager:
    """Manage webhook configurations"""
    
    def __init__(self, sdk: ContentProtectionSDK):
        self.sdk = sdk
    
    def create_webhook(self, url: str, events: List[str], secret: str = None) -> Dict[str, Any]:
        """Create a new webhook endpoint"""
        data = {
            "url": url,
            "events": events
        }
        
        if secret:
            data["secret"] = secret
        
        return self.sdk._make_request("POST", "/api/v1/webhooks", json=data)
    
    def list_webhooks(self) -> Dict[str, Any]:
        """List configured webhooks"""
        return self.sdk._make_request("GET", "/api/v1/webhooks")
    
    def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """Delete a webhook"""
        return self.sdk._make_request("DELETE", f"/api/v1/webhooks/{webhook_id}")
    
    @staticmethod
    def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
        """Verify webhook signature for security"""
        import hmac
        import hashlib
        
        expected_signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(
            f"sha256={expected_signature}",
            signature
        )


# Async version of the SDK
class AsyncContentProtectionSDK:
    """Async version of the Content Protection SDK"""
    
    def __init__(self, base_url: str = "https://api.contentprotection.ai"):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
    
    async def authenticate(self, email: str, password: str, remember_me: bool = True) -> Dict[str, Any]:
        """Async authentication"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v1/auth/login",
                json={
                    "email": email,
                    "password": password,
                    "remember_me": remember_me
                }
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                
                expires_in = data["expires_in"]
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
                
                return data
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make async API request"""
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        })
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, **kwargs) as response:
                response.raise_for_status()
                return await response.json()


# Example usage and complete workflow
def main():
    """Complete example workflow"""
    
    # Initialize SDK
    sdk = ContentProtectionSDK()
    
    # Authenticate
    sdk.authenticate("creator@example.com", "secure_password")
    
    # Initialize managers
    profiles = ProfileManager(sdk)
    scanning = ScanningManager(sdk)
    infringements = InfringementManager(sdk)
    takedowns = TakedownManager(sdk)
    webhooks = WebhookManager(sdk)
    
    # 1. Create a protected profile
    print("Creating protected profile...")
    profile = profiles.create_profile(
        name="Content Creator",
        platform="onlyfans",
        username="creator_username",
        keywords=["creator name", "username", "exclusive content"]
    )
    profile_id = profile["id"]
    print(f"Profile created with ID: {profile_id}")
    
    # 2. Upload reference content
    print("Uploading reference content...")
    reference_images = [
        "https://example.com/reference1.jpg",
        "https://example.com/reference2.jpg"
    ]
    
    signatures = profiles.upload_reference_content(profile_id, reference_images)
    print(f"Generated {signatures['signatures_generated']['face_encodings']} face encodings")
    
    # 3. Configure monitoring
    print("Configuring scan schedule...")
    scanning.configure_scan_schedule(
        profile_id=profile_id,
        frequency="daily",
        time="02:00",
        platforms=["google", "bing", "social_media"]
    )
    
    # 4. Trigger manual scan
    print("Triggering manual scan...")
    scan_result = scanning.trigger_manual_scan(profile_id)
    job_id = scan_result["job_id"]
    print(f"Scan initiated with job ID: {job_id}")
    
    # 5. Wait for scan completion
    print("Waiting for scan to complete...")
    try:
        final_status = scanning.wait_for_scan_completion(job_id, timeout=600)
        print(f"Scan completed! Results: {final_status['results']}")
    except TimeoutError:
        print("Scan is taking longer than expected. Check status later.")
        return
    
    # 6. Process infringements
    print("Processing detected infringements...")
    detected_infringements = infringements.list_infringements(
        profile_id=profile_id,
        status="detected",
        confidence_threshold=0.8
    )
    
    for infringement in detected_infringements["items"]:
        confidence = infringement["confidence_score"]
        url = infringement["url"]
        
        print(f"Found infringement at {url} (confidence: {confidence:.2f})")
        
        if confidence > 0.9:
            # High confidence - submit takedown immediately
            takedown = takedowns.submit_takedown(
                infringement_id=infringement["id"],
                urgency="high",
                additional_info="High-confidence match found through AI analysis"
            )
            print(f"Takedown submitted: {takedown['id']}")
            
        elif confidence > 0.8:
            # Medium confidence - mark for manual review
            infringements.update_infringement_status(
                infringement_id=infringement["id"],
                status="pending_review",
                notes="Medium confidence - requires manual verification"
            )
    
    # 7. Set up webhooks for notifications
    print("Setting up webhooks...")
    webhook = webhooks.create_webhook(
        url="https://your-app.com/webhooks/contentprotection",
        events=["scan.completed", "infringement.detected", "takedown.status_changed"],
        secret="your-webhook-secret"
    )
    print(f"Webhook created: {webhook['id']}")
    
    print("Setup complete! Your content is now being protected.")


if __name__ == "__main__":
    main()