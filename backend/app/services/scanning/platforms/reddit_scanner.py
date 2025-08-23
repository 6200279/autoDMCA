"""
Reddit API Integration
Searches Reddit for leaked content and discussions
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging
import base64
from urllib.parse import quote_plus

from .base_scanner import BaseScanner, ScanResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedditScanner(BaseScanner):
    """
    Reddit scanner using Reddit API
    PRD: "Scans major platforms: Reddit"
    """
    
    def __init__(self, region: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(region=region, rate_limit=60, **kwargs)  # 60 requests per minute
        
        # Reddit API configuration
        self.client_id = getattr(settings, 'REDDIT_CLIENT_ID', None)
        self.client_secret = getattr(settings, 'REDDIT_CLIENT_SECRET', None)
        self.user_agent = "AutoDMCA Content Scanner v1.0"
        
        # API endpoints
        self.base_url = "https://oauth.reddit.com"
        self.auth_url = "https://www.reddit.com/api/v1/access_token"
        
        # Authentication
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
        if not self.client_id or not self.client_secret:
            logger.warning("Reddit API credentials not configured")
    
    async def get_platform_name(self) -> str:
        return "reddit"
    
    async def _authenticate(self) -> bool:
        """Authenticate with Reddit API"""
        if not self.client_id or not self.client_secret:
            return False
        
        try:
            # Prepare authentication
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_b64}',
                'User-Agent': self.user_agent,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'client_credentials'
            }
            
            response = await self._make_request(
                self.auth_url,
                method='POST',
                headers=headers,
                data=data
            )
            
            if response and response.status == 200:
                token_data = await response.json()
                self.access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)
                
                self.token_expires_at = datetime.now(timezone.utc).replace(
                    microsecond=0
                ) + timedelta(seconds=expires_in - 60)  # 60s buffer
                
                logger.info("Reddit API authentication successful")
                return True
            else:
                logger.error(f"Reddit authentication failed with status: {response.status if response else 'No response'}")
                return False
                
        except Exception as e:
            logger.error(f"Reddit authentication error: {e}")
            return False
    
    async def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid access token"""
        if not self.access_token or not self.token_expires_at:
            return await self._authenticate()
        
        if datetime.now(timezone.utc) >= self.token_expires_at:
            return await self._authenticate()
        
        return True
    
    async def _make_reddit_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make authenticated request to Reddit API"""
        if not await self._ensure_authenticated():
            logger.error("Reddit authentication required")
            return None
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'User-Agent': self.user_agent
        }
        
        url = f"{self.base_url}{endpoint}"
        return await self._fetch_json(url, params=params, headers=headers)
    
    async def search(
        self,
        query: str,
        limit: int = 50,
        include_metadata: bool = True,
        **kwargs
    ) -> List[ScanResult]:
        """
        Search Reddit for posts and comments
        """
        if not self.client_id or not self.client_secret:
            logger.warning("Reddit API not configured, using fallback search")
            return await self._fallback_search(query, limit)
        
        results = []
        
        try:
            # Search posts
            post_results = await self._search_posts(query, limit // 2)
            results.extend(post_results)
            
            # Search comments if we need more results
            if len(results) < limit:
                comment_results = await self._search_comments(query, limit - len(results))
                results.extend(comment_results)
            
            # Search specific subreddits known for leaks
            if len(results) < limit:
                leak_subreddits = [
                    'onlyfansleaks', 'patreonleaks', 'megalinks', 'opendirectories',
                    'piracy', 'leakshub', 'leaks', 'nsfwleaks'
                ]
                
                for subreddit in leak_subreddits[:3]:  # Limit subreddit searches
                    if len(results) >= limit:
                        break
                    
                    subreddit_results = await self._search_subreddit(
                        subreddit, query, min(10, limit - len(results))
                    )
                    results.extend(subreddit_results)
        
        except Exception as e:
            logger.error(f"Reddit search error for query '{query}': {e}")
            # Fall back to web scraping
            return await self._fallback_search(query, limit)
        
        logger.info(f"Reddit search found {len(results)} results for query: {query}")
        return results[:limit]
    
    async def _search_posts(self, query: str, limit: int) -> List[ScanResult]:
        """Search Reddit posts"""
        results = []
        
        params = {
            'q': query,
            'limit': min(limit, 25),  # Reddit API limit
            'sort': 'relevance',
            'type': 'link,self',
            'include_over_18': 'true'  # Include NSFW content
        }
        
        data = await self._make_reddit_request('/search', params=params)
        
        if not data or 'data' not in data or 'children' not in data['data']:
            return results
        
        for item in data['data']['children']:
            try:
                post_data = item['data']
                scan_result = await self._process_reddit_post(post_data, query)
                if scan_result:
                    results.append(scan_result)
            except Exception as e:
                logger.error(f"Error processing Reddit post: {e}")
                continue
        
        return results
    
    async def _search_comments(self, query: str, limit: int) -> List[ScanResult]:
        """Search Reddit comments"""
        results = []
        
        # Reddit doesn't have a direct comment search in the official API
        # We would need to use third-party services like Pushshift
        # For now, return empty list
        
        return results
    
    async def _search_subreddit(self, subreddit: str, query: str, limit: int) -> List[ScanResult]:
        """Search within a specific subreddit"""
        results = []
        
        params = {
            'q': f'subreddit:{subreddit} {query}',
            'limit': min(limit, 25),
            'sort': 'new',
            'include_over_18': 'true'
        }
        
        data = await self._make_reddit_request('/search', params=params)
        
        if not data or 'data' not in data or 'children' not in data['data']:
            return results
        
        for item in data['data']['children']:
            try:
                post_data = item['data']
                scan_result = await self._process_reddit_post(post_data, query)
                if scan_result:
                    results.append(scan_result)
            except Exception as e:
                logger.error(f"Error processing subreddit post: {e}")
                continue
        
        return results
    
    async def _process_reddit_post(self, post_data: Dict[str, Any], query: str) -> Optional[ScanResult]:
        """Process individual Reddit post"""
        try:
            url = f"https://reddit.com{post_data.get('permalink', '')}"
            title = post_data.get('title', '')
            description = post_data.get('selftext', '') or post_data.get('body', '')
            author = post_data.get('author', '')
            subreddit = post_data.get('subreddit', '')
            
            # Extract media URLs
            media_urls = []
            
            # Check for direct image/video links
            if post_data.get('url'):
                post_url = post_data['url']
                if self._is_valid_media_url(post_url):
                    media_urls.append(post_url)
            
            # Check Reddit video
            if post_data.get('media') and post_data['media'].get('reddit_video'):
                video_data = post_data['media']['reddit_video']
                if video_data.get('fallback_url'):
                    media_urls.append(video_data['fallback_url'])
            
            # Check gallery
            if post_data.get('is_gallery') and post_data.get('media_metadata'):
                for media_id, media_info in post_data['media_metadata'].items():
                    if media_info.get('s') and media_info['s'].get('u'):
                        media_url = media_info['s']['u'].replace('&amp;', '&')
                        media_urls.append(media_url)
            
            # Extract thumbnail
            thumbnail_url = None
            if post_data.get('thumbnail') and post_data['thumbnail'] not in ['self', 'default', 'nsfw']:
                thumbnail_url = post_data['thumbnail']
            
            # Extract creation time
            created_at = None
            if post_data.get('created_utc'):
                created_at = datetime.fromtimestamp(post_data['created_utc'], tz=timezone.utc)
            
            # Build engagement stats
            engagement_stats = {
                'score': post_data.get('score', 0),
                'upvote_ratio': post_data.get('upvote_ratio', 0),
                'num_comments': post_data.get('num_comments', 0),
                'awards_received': len(post_data.get('all_awardings', []))
            }
            
            # Calculate confidence score
            confidence_score = self._calculate_reddit_relevance(post_data, query)
            
            # Build metadata
            metadata = {
                'subreddit': subreddit,
                'post_id': post_data.get('id', ''),
                'post_type': 'link' if post_data.get('url') else 'self',
                'nsfw': post_data.get('over_18', False),
                'locked': post_data.get('locked', False),
                'archived': post_data.get('archived', False),
                'awards': post_data.get('total_awards_received', 0),
                'crosspost_parent': post_data.get('crosspost_parent_list', [])
            }
            
            return ScanResult(
                url=url,
                platform="reddit",
                title=self._clean_text(title),
                description=self._clean_text(description[:500]),  # Limit description length
                thumbnail_url=thumbnail_url,
                media_urls=list(set(media_urls)),  # Remove duplicates
                author=author,
                created_at=created_at,
                engagement_stats=engagement_stats,
                search_query=query,
                region=self.region.get('region_id') if self.region else None,
                confidence_score=confidence_score,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error processing Reddit post: {e}")
            return None
    
    def _calculate_reddit_relevance(self, post_data: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for Reddit post"""
        score = 0.5  # Base score
        
        query_terms = query.lower().split()
        title = post_data.get('title', '').lower()
        content = post_data.get('selftext', '').lower()
        subreddit = post_data.get('subreddit', '').lower()
        
        # Score based on query term matches
        for term in query_terms:
            if term in title:
                score += 0.3
            if term in content:
                score += 0.2
            if term in subreddit:
                score += 0.1
        
        # Boost score for leak-related subreddits
        leak_subreddits = [
            'onlyfansleaks', 'patreonleaks', 'megalinks', 'leaks',
            'nsfwleaks', 'piracy', 'opendirectories'
        ]
        
        if subreddit in leak_subreddits:
            score += 0.4
        
        # Boost for NSFW content (more likely to be adult content)
        if post_data.get('over_18'):
            score += 0.2
        
        # Boost for posts with high engagement
        score_value = post_data.get('score', 0)
        if score_value > 100:
            score += 0.1
        if score_value > 1000:
            score += 0.1
        
        # Boost for posts with media
        if (post_data.get('url') and 
            (post_data.get('post_hint') in ['image', 'hosted:video'] or
             self._is_valid_media_url(post_data['url']))):
            score += 0.3
        
        return min(score, 1.0)
    
    async def _fallback_search(self, query: str, limit: int) -> List[ScanResult]:
        """
        Fallback search using Reddit's web interface
        """
        results = []
        
        try:
            # Use Reddit's search without authentication
            search_url = "https://www.reddit.com/search.json"
            params = {
                'q': query,
                'limit': min(limit, 25),
                'sort': 'relevance',
                'include_over_18': 'on'
            }
            
            headers = {
                'User-Agent': self.user_agent
            }
            
            response_data = await self._fetch_json(search_url, params=params, headers=headers)
            
            if response_data and 'data' in response_data and 'children' in response_data['data']:
                for item in response_data['data']['children']:
                    try:
                        post_data = item['data']
                        scan_result = await self._process_reddit_post(post_data, query)
                        if scan_result:
                            results.append(scan_result)
                    except Exception as e:
                        logger.error(f"Error processing fallback Reddit post: {e}")
                        continue
            
        except Exception as e:
            logger.error(f"Reddit fallback search error: {e}")
        
        return results
    
    async def search_user(
        self,
        username: str,
        limit: int = 25,
        **kwargs
    ) -> List[ScanResult]:
        """Search posts by a specific user"""
        query = f"author:{username}"
        return await self.search(query, limit=limit, **kwargs)
    
    async def search_subreddit_direct(
        self,
        subreddit: str,
        query: str = "",
        limit: int = 25,
        sort: str = "new",
        **kwargs
    ) -> List[ScanResult]:
        """Search within a specific subreddit directly"""
        endpoint = f"/r/{subreddit}/{sort}"
        params = {
            'limit': min(limit, 25)
        }
        
        if query:
            params['q'] = query
        
        data = await self._make_reddit_request(endpoint, params=params)
        
        results = []
        if data and 'data' in data and 'children' in data['data']:
            for item in data['data']['children']:
                try:
                    post_data = item['data']
                    scan_result = await self._process_reddit_post(post_data, query or subreddit)
                    if scan_result:
                        results.append(scan_result)
                except Exception as e:
                    logger.error(f"Error processing subreddit post: {e}")
                    continue
        
        return results
    
    async def health_check(self) -> bool:
        """Check if Reddit scanner is healthy"""
        try:
            if not self.client_id or not self.client_secret:
                # Test fallback search
                results = await self._fallback_search("test", 1)
                return len(results) > 0
            else:
                # Test API authentication
                return await self._ensure_authenticated()
        except Exception as e:
            logger.error(f"Reddit scanner health check failed: {e}")
            return False