"""
Search Engine Delisting Service

Provides functionality to submit copyright removal requests to major search engines
(Google, Bing, Yahoo) to delist infringing URLs from search results.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse, urlencode
import base64

import httpx
from bs4 import BeautifulSoup

from ..models.takedown import TakedownRequest, TakedownStatus
from ..models.hosting import DMCAAgent
from ..templates.template_renderer import TemplateRenderer
from ..utils.cache import CacheManager
from ..utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class SearchEngineType:
    """Search engine identifiers."""
    
    GOOGLE = "google"
    BING = "bing"
    YAHOO = "yahoo"
    DUCKDUCKGO = "duckduckgo"


class DelistingStatus:
    """Status of delisting requests."""
    
    PENDING = "pending"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELISTED = "delisted"
    FAILED = "failed"


class SearchDelistingService:
    """
    Service for submitting copyright removal requests to search engines.
    """
    
    def __init__(
        self,
        google_api_key: Optional[str] = None,
        google_custom_search_id: Optional[str] = None,
        bing_api_key: Optional[str] = None,
        template_renderer: Optional[TemplateRenderer] = None,
        cache_manager: Optional[CacheManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
        timeout: int = 30
    ):
        """
        Initialize search delisting service.
        
        Args:
            google_api_key: Google Custom Search API key
            google_custom_search_id: Google Custom Search Engine ID
            bing_api_key: Bing Web Search API key
            template_renderer: Template renderer for removal requests
            cache_manager: Cache manager for tracking requests
            rate_limiter: Rate limiter for API calls
            timeout: HTTP timeout in seconds
        """
        self.google_api_key = google_api_key
        self.google_custom_search_id = google_custom_search_id
        self.bing_api_key = bing_api_key
        self.template_renderer = template_renderer or TemplateRenderer()
        self.cache_manager = cache_manager or CacheManager()
        self.rate_limiter = rate_limiter or RateLimiter(max_calls=30, time_window=60)
        self.timeout = timeout
        
        # HTTP client configuration
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            headers={
                'User-Agent': 'AutoDMCA/1.0 (+https://autodmca.com/bot)'
            }
        )
        
        # Search engine endpoints and configurations
        self.search_engines = {
            SearchEngineType.GOOGLE: {
                'name': 'Google',
                'removal_url': 'https://www.google.com/webmasters/tools/legal-removal-request',
                'search_api': 'https://www.googleapis.com/customsearch/v1',
                'verification_method': self._verify_google_delisting,
                'form_handler': self._submit_google_removal_form,
            },
            SearchEngineType.BING: {
                'name': 'Bing',
                'removal_url': 'https://www.bing.com/webmaster/tools/contentremoval-report',
                'search_api': 'https://api.cognitive.microsoft.com/bing/v7.0/search',
                'verification_method': self._verify_bing_delisting,
                'form_handler': self._submit_bing_removal_form,
            },
            SearchEngineType.YAHOO: {
                'name': 'Yahoo',
                'removal_url': 'https://help.yahoo.com/kb/search/remove-content-search-results-sln2000.html',
                'verification_method': self._verify_yahoo_delisting,
                'form_handler': self._submit_yahoo_removal_form,
            }
        }
    
    async def submit_delisting_request(
        self,
        takedown_requests: List[TakedownRequest],
        search_engine: str = SearchEngineType.GOOGLE,
        agent_contact: Optional[DMCAAgent] = None,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Submit delisting request to search engine.
        
        Args:
            takedown_requests: List of takedown requests to delist
            search_engine: Target search engine
            agent_contact: DMCA agent contact information
            batch_size: Maximum URLs per request
        
        Returns:
            Dict with submission results
        """
        try:
            if search_engine not in self.search_engines:
                raise ValueError(f"Unsupported search engine: {search_engine}")
            
            if not takedown_requests:
                raise ValueError("No takedown requests provided")
            
            # Rate limit check
            await self.rate_limiter.acquire()
            
            # Split into batches if needed
            results = []
            for i in range(0, len(takedown_requests), batch_size):
                batch = takedown_requests[i:i + batch_size]
                batch_result = await self._submit_batch_delisting(
                    batch, search_engine, agent_contact
                )
                results.append(batch_result)
            
            # Aggregate results
            total_submitted = sum(r.get('submitted_count', 0) for r in results)
            total_failed = sum(r.get('failed_count', 0) for r in results)
            
            return {
                'success': total_submitted > 0,
                'search_engine': search_engine,
                'total_urls': len(takedown_requests),
                'submitted_count': total_submitted,
                'failed_count': total_failed,
                'batch_results': results,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Delisting submission failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'search_engine': search_engine,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _submit_batch_delisting(
        self,
        takedown_requests: List[TakedownRequest],
        search_engine: str,
        agent_contact: Optional[DMCAAgent]
    ) -> Dict[str, Any]:
        """Submit a batch of URLs for delisting."""
        try:
            engine_config = self.search_engines[search_engine]
            
            # Generate removal request content
            removal_content = self.template_renderer.render_search_delisting_request(
                takedown_requests,
                agent_contact
            )
            
            # Prepare submission data
            submission_data = {
                'urls': [str(req.infringement_data.infringing_url) for req in takedown_requests],
                'request_body': removal_content['body'],
                'contact_email': agent_contact.email if agent_contact else takedown_requests[0].creator_profile.email,
                'contact_name': agent_contact.name if agent_contact else takedown_requests[0].creator_profile.public_name,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Submit to search engine
            form_handler = engine_config['form_handler']
            submission_result = await form_handler(submission_data)
            
            # Track submission
            if submission_result.get('success'):
                await self._track_delisting_request(
                    takedown_requests, search_engine, submission_result
                )
            
            return {
                'search_engine': search_engine,
                'submitted_count': len(takedown_requests) if submission_result.get('success') else 0,
                'failed_count': 0 if submission_result.get('success') else len(takedown_requests),
                'submission_id': submission_result.get('submission_id'),
                'urls': submission_data['urls'],
                'status': DelistingStatus.SUBMITTED if submission_result.get('success') else DelistingStatus.FAILED
            }
            
        except Exception as e:
            logger.error(f"Batch delisting submission failed: {str(e)}")
            return {
                'search_engine': search_engine,
                'submitted_count': 0,
                'failed_count': len(takedown_requests),
                'error': str(e)
            }
    
    async def _submit_google_removal_form(self, submission_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit removal request to Google's form.
        
        Note: Google's legal removal process is typically manual via their web form.
        This implementation provides the framework for automated submission.
        """
        try:
            # Google requires manual submission through their web form
            # We'll simulate the process and provide the data formatted for submission
            
            # For demonstration, we'll format the data as would be needed
            google_submission = {
                'type': 'copyright',
                'urls': submission_data['urls'],
                'description': submission_data['request_body'],
                'requester_email': submission_data['contact_email'],
                'requester_name': submission_data['contact_name']
            }
            
            # In a production environment, you might use browser automation
            # or work with Google's official APIs if available
            
            # Generate submission ID for tracking
            submission_id = f"google_{int(datetime.utcnow().timestamp())}"
            
            logger.info(f"Google removal request prepared: {submission_id}")
            
            # Store submission data for manual processing
            await self._store_manual_submission('google', submission_id, google_submission)
            
            return {
                'success': True,
                'submission_id': submission_id,
                'method': 'manual_form',
                'note': 'Requires manual submission through Google\'s web form'
            }
            
        except Exception as e:
            logger.error(f"Google form submission failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _submit_bing_removal_form(self, submission_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit removal request to Bing's content removal form.
        """
        try:
            # Bing also primarily uses web forms for copyright removal
            # Similar to Google, this would require manual submission or automation
            
            bing_submission = {
                'reason': 'copyright',
                'urls': submission_data['urls'],
                'explanation': submission_data['request_body'],
                'contact_info': {
                    'email': submission_data['contact_email'],
                    'name': submission_data['contact_name']
                }
            }
            
            submission_id = f"bing_{int(datetime.utcnow().timestamp())}"
            
            logger.info(f"Bing removal request prepared: {submission_id}")
            
            # Store for manual processing
            await self._store_manual_submission('bing', submission_id, bing_submission)
            
            return {
                'success': True,
                'submission_id': submission_id,
                'method': 'manual_form',
                'note': 'Requires manual submission through Bing\'s web form'
            }
            
        except Exception as e:
            logger.error(f"Bing form submission failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _submit_yahoo_removal_form(self, submission_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit removal request to Yahoo (limited options)."""
        try:
            # Yahoo has more limited removal options
            # Usually requires going through their help system
            
            submission_id = f"yahoo_{int(datetime.utcnow().timestamp())}"
            
            yahoo_submission = {
                'urls': submission_data['urls'],
                'request': submission_data['request_body'],
                'contact': submission_data['contact_email']
            }
            
            await self._store_manual_submission('yahoo', submission_id, yahoo_submission)
            
            return {
                'success': True,
                'submission_id': submission_id,
                'method': 'help_system',
                'note': 'Yahoo removal requires manual contact through help system'
            }
            
        except Exception as e:
            logger.error(f"Yahoo submission failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def verify_delisting_status(
        self,
        urls: List[str],
        search_engine: str = SearchEngineType.GOOGLE
    ) -> Dict[str, Dict[str, Any]]:
        """
        Verify if URLs have been delisted from search results.
        
        Args:
            urls: List of URLs to check
            search_engine: Search engine to check
        
        Returns:
            Dict mapping URLs to their delisting status
        """
        try:
            if search_engine not in self.search_engines:
                raise ValueError(f"Unsupported search engine: {search_engine}")
            
            engine_config = self.search_engines[search_engine]
            verification_method = engine_config['verification_method']
            
            results = {}
            
            # Check each URL individually to avoid rate limits
            for url in urls:
                await self.rate_limiter.acquire()
                
                try:
                    status = await verification_method(url)
                    results[url] = status
                    
                    # Small delay between checks
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Failed to verify {url}: {str(e)}")
                    results[url] = {
                        'delisted': False,
                        'error': str(e),
                        'checked_at': datetime.utcnow().isoformat()
                    }
            
            return results
            
        except Exception as e:
            logger.error(f"Delisting verification failed: {str(e)}")
            return {url: {'error': str(e)} for url in urls}
    
    async def _verify_google_delisting(self, url: str) -> Dict[str, Any]:
        """Verify if URL is delisted from Google."""
        try:
            if not self.google_api_key or not self.google_custom_search_id:
                # Fallback to site: search without API
                return await self._verify_via_site_search(url, 'google')
            
            # Use Custom Search API to check if URL appears in results
            search_params = {
                'key': self.google_api_key,
                'cx': self.google_custom_search_id,
                'q': f'site:{urlparse(url).netloc}',
                'num': 10
            }
            
            api_url = f"{self.search_engines[SearchEngineType.GOOGLE]['search_api']}?{urlencode(search_params)}"
            
            response = await self.http_client.get(api_url)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            
            # Check if the specific URL appears in results
            url_found = any(item.get('link') == url for item in items)
            
            return {
                'delisted': not url_found,
                'found_in_results': url_found,
                'total_results': len(items),
                'checked_at': datetime.utcnow().isoformat(),
                'method': 'api'
            }
            
        except Exception as e:
            logger.error(f"Google verification failed for {url}: {str(e)}")
            return {
                'delisted': False,
                'error': str(e),
                'checked_at': datetime.utcnow().isoformat()
            }
    
    async def _verify_bing_delisting(self, url: str) -> Dict[str, Any]:
        """Verify if URL is delisted from Bing."""
        try:
            if not self.bing_api_key:
                return await self._verify_via_site_search(url, 'bing')
            
            # Use Bing Search API
            headers = {
                'Ocp-Apim-Subscription-Key': self.bing_api_key
            }
            
            search_params = {
                'q': f'site:{urlparse(url).netloc}',
                'count': 10
            }
            
            api_url = f"{self.search_engines[SearchEngineType.BING]['search_api']}?{urlencode(search_params)}"
            
            response = await self.http_client.get(api_url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            web_pages = data.get('webPages', {}).get('value', [])
            
            # Check if URL appears in results
            url_found = any(page.get('url') == url for page in web_pages)
            
            return {
                'delisted': not url_found,
                'found_in_results': url_found,
                'total_results': len(web_pages),
                'checked_at': datetime.utcnow().isoformat(),
                'method': 'api'
            }
            
        except Exception as e:
            logger.error(f"Bing verification failed for {url}: {str(e)}")
            return {
                'delisted': False,
                'error': str(e),
                'checked_at': datetime.utcnow().isoformat()
            }
    
    async def _verify_yahoo_delisting(self, url: str) -> Dict[str, Any]:
        """Verify if URL is delisted from Yahoo."""
        # Yahoo uses Bing's search results, so check via site search
        return await self._verify_via_site_search(url, 'yahoo')
    
    async def _verify_via_site_search(self, url: str, search_engine: str) -> Dict[str, Any]:
        """
        Verify delisting by performing a site: search without API.
        This is a fallback method when APIs are not available.
        """
        try:
            parsed_url = urlparse(url)
            search_query = f"site:{parsed_url.netloc}"
            
            # Search engine URLs
            search_urls = {
                'google': f'https://www.google.com/search?q={urlencode({"q": search_query})}',
                'bing': f'https://www.bing.com/search?q={urlencode({"q": search_query})}',
                'yahoo': f'https://search.yahoo.com/search?p={search_query}'
            }
            
            if search_engine not in search_urls:
                raise ValueError(f"Unsupported search engine: {search_engine}")
            
            search_url = search_urls[search_engine]
            
            # Perform search with appropriate headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = await self.http_client.get(search_url, headers=headers)
            response.raise_for_status()
            
            # Parse HTML to check if URL appears
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for the URL in search results
            # This is a simplified check - production code would be more sophisticated
            page_text = soup.get_text().lower()
            url_found = url.lower() in page_text or parsed_url.netloc.lower() in page_text
            
            return {
                'delisted': not url_found,
                'found_in_results': url_found,
                'checked_at': datetime.utcnow().isoformat(),
                'method': 'site_search',
                'note': 'Basic site: search verification'
            }
            
        except Exception as e:
            logger.error(f"Site search verification failed for {url}: {str(e)}")
            return {
                'delisted': False,
                'error': str(e),
                'checked_at': datetime.utcnow().isoformat()
            }
    
    async def _track_delisting_request(
        self,
        takedown_requests: List[TakedownRequest],
        search_engine: str,
        submission_result: Dict[str, Any]
    ) -> None:
        """Track delisting request for follow-up."""
        try:
            tracking_data = {
                'submission_id': submission_result.get('submission_id'),
                'search_engine': search_engine,
                'urls': [str(req.infringement_data.infringing_url) for req in takedown_requests],
                'takedown_ids': [str(req.id) for req in takedown_requests],
                'status': DelistingStatus.SUBMITTED,
                'submitted_at': datetime.utcnow().isoformat(),
                'agent_email': submission_result.get('contact_email')
            }
            
            # Store in cache for tracking
            cache_key = f"delisting:{submission_result.get('submission_id')}"
            await self.cache_manager.set(
                cache_key, 
                tracking_data, 
                ttl=timedelta(days=90)  # Keep tracking data for 3 months
            )
            
            # Update takedown request statuses
            for request in takedown_requests:
                request.update_status(TakedownStatus.SEARCH_DELISTING_REQUESTED)
            
        except Exception as e:
            logger.error(f"Failed to track delisting request: {str(e)}")
    
    async def _store_manual_submission(
        self,
        search_engine: str,
        submission_id: str,
        submission_data: Dict[str, Any]
    ) -> None:
        """Store manual submission data for processing."""
        try:
            manual_submission = {
                'submission_id': submission_id,
                'search_engine': search_engine,
                'data': submission_data,
                'requires_manual_action': True,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'pending_manual_submission'
            }
            
            cache_key = f"manual_submission:{submission_id}"
            await self.cache_manager.set(
                cache_key,
                manual_submission,
                ttl=timedelta(days=30)
            )
            
            logger.info(f"Stored manual submission {submission_id} for {search_engine}")
            
        except Exception as e:
            logger.error(f"Failed to store manual submission: {str(e)}")
    
    async def get_delisting_status(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a delisting request.
        
        Args:
            submission_id: Submission ID to check
        
        Returns:
            Dict with delisting status information
        """
        try:
            cache_key = f"delisting:{submission_id}"
            return await self.cache_manager.get(cache_key)
        except Exception as e:
            logger.error(f"Failed to get delisting status: {str(e)}")
            return None
    
    async def get_pending_manual_submissions(self) -> List[Dict[str, Any]]:
        """Get list of submissions requiring manual action."""
        # This would query all manual submissions from storage
        # Implementation depends on your specific cache/database setup
        return []
    
    async def bulk_verify_delisting(
        self,
        urls: List[str],
        search_engines: List[str] = None
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Verify delisting status across multiple search engines.
        
        Args:
            urls: List of URLs to verify
            search_engines: List of search engines to check (defaults to all)
        
        Returns:
            Nested dict: {search_engine: {url: status_info}}
        """
        if search_engines is None:
            search_engines = [SearchEngineType.GOOGLE, SearchEngineType.BING]
        
        results = {}
        
        for engine in search_engines:
            if engine in self.search_engines:
                results[engine] = await self.verify_delisting_status(urls, engine)
        
        return results
    
    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        await self.http_client.aclose()