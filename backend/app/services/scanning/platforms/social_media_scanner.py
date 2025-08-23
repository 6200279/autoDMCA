"""
Social Media Platform Scanners
Scanners for Instagram, Twitter, TikTok and other social media platforms
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import logging
import json
import re
from urllib.parse import quote_plus, urlparse

from .base_scanner import BaseScanner, ScanResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class InstagramScanner(BaseScanner):
    """
    Instagram scanner for content discovery
    PRD: "Scans major platforms: Instagram"
    """
    
    def __init__(self, region: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(region=region, rate_limit=30, **kwargs)  # Conservative rate limit
        
        # Instagram doesn't have a public API for content search
        # We'll use web scraping techniques
        self.base_url = "https://www.instagram.com"
        
    async def get_platform_name(self) -> str:
        return "instagram"
    
    async def search(
        self,
        query: str,
        limit: int = 50,
        include_metadata: bool = True,
        **kwargs
    ) -> List[ScanResult]:
        """
        Search Instagram using web scraping
        Note: Instagram heavily restricts scraping, this is a basic implementation
        """
        results = []
        
        try:
            # Search hashtags
            hashtag_results = await self._search_hashtags(query, limit // 2)
            results.extend(hashtag_results)
            
            # Search users
            if len(results) < limit:
                user_results = await self._search_users(query, limit - len(results))
                results.extend(user_results)
                
        except Exception as e:
            logger.error(f"Instagram search error for query '{query}': {e}")
        
        logger.info(f"Instagram search found {len(results)} results for query: {query}")
        return results[:limit]
    
    async def _search_hashtags(self, query: str, limit: int) -> List[ScanResult]:
        """Search Instagram hashtags"""
        results = []
        
        try:
            # Create hashtag from query (remove spaces, special chars)
            hashtag = re.sub(r'[^a-zA-Z0-9]', '', query.replace(' ', ''))
            
            # Try to get hashtag page
            hashtag_url = f"{self.base_url}/explore/tags/{hashtag}/"
            
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
            }
            
            html_content = await self._fetch_html(hashtag_url, headers=headers)
            
            if html_content:
                # Extract JSON data from script tags
                json_data = self._extract_instagram_json(html_content)
                
                if json_data:
                    posts = self._extract_posts_from_json(json_data, hashtag, query)
                    results.extend(posts[:limit])
                    
        except Exception as e:
            logger.error(f"Error searching Instagram hashtags: {e}")
        
        return results
    
    async def _search_users(self, query: str, limit: int) -> List[ScanResult]:
        """Search Instagram users"""
        results = []
        
        try:
            # Try direct username lookup
            username = query.replace(' ', '').lower()
            user_url = f"{self.base_url}/{username}/"
            
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            html_content = await self._fetch_html(user_url, headers=headers)
            
            if html_content and "Page Not Found" not in html_content:
                # Extract user profile data
                json_data = self._extract_instagram_json(html_content)
                
                if json_data:
                    user_posts = self._extract_user_posts_from_json(json_data, username, query)
                    results.extend(user_posts[:limit])
                    
        except Exception as e:
            logger.error(f"Error searching Instagram users: {e}")
        
        return results
    
    def _extract_instagram_json(self, html_content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON data from Instagram page"""
        try:
            # Look for window._sharedData
            pattern = r'window\._sharedData = ({.*?});'
            match = re.search(pattern, html_content)
            
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
                
        except Exception as e:
            logger.error(f"Error extracting Instagram JSON: {e}")
        
        return None
    
    def _extract_posts_from_json(
        self,
        json_data: Dict[str, Any],
        hashtag: str,
        query: str
    ) -> List[ScanResult]:
        """Extract posts from Instagram JSON data"""
        results = []
        
        try:
            # Navigate through Instagram's data structure
            entry_data = json_data.get('entry_data', {})
            hashtag_page = entry_data.get('TagPage', [])
            
            if hashtag_page:
                graphql = hashtag_page[0].get('graphql', {})
                hashtag_data = graphql.get('hashtag', {})
                edge_hashtag_to_media = hashtag_data.get('edge_hashtag_to_media', {})
                edges = edge_hashtag_to_media.get('edges', [])
                
                for edge in edges[:50]:  # Limit processing
                    node = edge.get('node', {})
                    
                    if node:
                        result = self._process_instagram_post(node, hashtag, query)
                        if result:
                            results.append(result)
                            
        except Exception as e:
            logger.error(f"Error extracting posts from Instagram JSON: {e}")
        
        return results
    
    def _extract_user_posts_from_json(
        self,
        json_data: Dict[str, Any],
        username: str,
        query: str
    ) -> List[ScanResult]:
        """Extract user posts from Instagram JSON data"""
        results = []
        
        try:
            entry_data = json_data.get('entry_data', {})
            profile_page = entry_data.get('ProfilePage', [])
            
            if profile_page:
                graphql = profile_page[0].get('graphql', {})
                user = graphql.get('user', {})
                edge_owner_to_timeline_media = user.get('edge_owner_to_timeline_media', {})
                edges = edge_owner_to_timeline_media.get('edges', [])
                
                for edge in edges[:50]:  # Limit processing
                    node = edge.get('node', {})
                    
                    if node:
                        result = self._process_instagram_post(node, username, query)
                        if result:
                            results.append(result)
                            
        except Exception as e:
            logger.error(f"Error extracting user posts from Instagram JSON: {e}")
        
        return results
    
    def _process_instagram_post(
        self,
        node: Dict[str, Any],
        context: str,
        query: str
    ) -> Optional[ScanResult]:
        """Process individual Instagram post"""
        try:
            post_id = node.get('id')
            shortcode = node.get('shortcode')
            
            if not shortcode:
                return None
            
            url = f"{self.base_url}/p/{shortcode}/"
            
            # Extract media URLs
            media_urls = []
            display_url = node.get('display_url')
            if display_url:
                media_urls.append(display_url)
            
            # Check for video
            video_url = None
            if node.get('is_video') and node.get('video_url'):
                video_url = node['video_url']
                media_urls.append(video_url)
            
            # Extract caption
            caption = ""
            edge_media_to_caption = node.get('edge_media_to_caption', {})
            edges = edge_media_to_caption.get('edges', [])
            if edges:
                caption = edges[0].get('node', {}).get('text', '')
            
            # Extract owner info
            owner = node.get('owner', {})
            author = owner.get('username', '')
            
            # Extract engagement stats
            engagement_stats = {
                'likes': node.get('edge_media_preview_like', {}).get('count', 0),
                'comments': node.get('edge_media_to_comment', {}).get('count', 0),
                'views': node.get('video_view_count', 0) if node.get('is_video') else None
            }
            
            # Extract creation time
            created_at = None
            if node.get('taken_at_timestamp'):
                created_at = datetime.fromtimestamp(
                    node['taken_at_timestamp'], 
                    tz=timezone.utc
                )
            
            # Calculate confidence score
            confidence_score = self._calculate_instagram_relevance(node, caption, query)
            
            # Build metadata
            metadata = {
                'post_id': post_id,
                'shortcode': shortcode,
                'is_video': node.get('is_video', False),
                'accessibility_caption': node.get('accessibility_caption', ''),
                'context': context,  # hashtag or username
                'owner_id': owner.get('id'),
                'owner_is_verified': owner.get('is_verified', False)
            }
            
            return ScanResult(
                url=url,
                platform="instagram",
                title=f"Instagram post by @{author}",
                description=self._clean_text(caption[:300]),
                image_url=display_url,
                video_url=video_url,
                thumbnail_url=node.get('thumbnail_src'),
                media_urls=media_urls,
                author=author,
                created_at=created_at,
                engagement_stats=engagement_stats,
                search_query=query,
                region=self.region.get('region_id') if self.region else None,
                confidence_score=confidence_score,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error processing Instagram post: {e}")
            return None
    
    def _calculate_instagram_relevance(
        self,
        node: Dict[str, Any],
        caption: str,
        query: str
    ) -> float:
        """Calculate relevance score for Instagram post"""
        score = 0.5  # Base score
        
        query_terms = query.lower().split()
        caption_lower = caption.lower()
        
        # Score based on query term matches in caption
        for term in query_terms:
            if term in caption_lower:
                score += 0.3
        
        # Boost score for high engagement
        likes = node.get('edge_media_preview_like', {}).get('count', 0)
        comments = node.get('edge_media_to_comment', {}).get('count', 0)
        
        if likes > 1000:
            score += 0.2
        if comments > 100:
            score += 0.1
        
        # Boost for video content
        if node.get('is_video'):
            score += 0.1
        
        return min(score, 1.0)
    
    async def health_check(self) -> bool:
        """Check if Instagram scanner is healthy"""
        try:
            # Simple test to see if we can access Instagram
            response = await self._make_request(self.base_url)
            return response is not None
        except Exception as e:
            logger.error(f"Instagram scanner health check failed: {e}")
            return False


class TwitterScanner(BaseScanner):
    """
    Twitter/X scanner for content discovery
    PRD: "Scans major platforms: Twitter"
    """
    
    def __init__(self, region: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(region=region, rate_limit=300, **kwargs)  # Twitter API v2 limit
        
        # Twitter API configuration
        self.bearer_token = getattr(settings, 'TWITTER_BEARER_TOKEN', None)
        self.base_url = "https://api.twitter.com/2"
        
        if not self.bearer_token:
            logger.warning("Twitter API bearer token not configured")
    
    async def get_platform_name(self) -> str:
        return "twitter"
    
    async def search(
        self,
        query: str,
        limit: int = 50,
        include_metadata: bool = True,
        **kwargs
    ) -> List[ScanResult]:
        """
        Search Twitter using API v2
        """
        if not self.bearer_token:
            logger.warning("Twitter API not configured, using fallback search")
            return await self._fallback_search(query, limit)
        
        results = []
        
        try:
            # Search recent tweets
            recent_results = await self._search_recent_tweets(query, limit)
            results.extend(recent_results)
            
        except Exception as e:
            logger.error(f"Twitter search error for query '{query}': {e}")
            return await self._fallback_search(query, limit)
        
        logger.info(f"Twitter search found {len(results)} results for query: {query}")
        return results[:limit]
    
    async def _search_recent_tweets(self, query: str, limit: int) -> List[ScanResult]:
        """Search recent tweets using Twitter API v2"""
        results = []
        
        params = {
            'query': query,
            'max_results': min(limit, 100),  # API limit
            'tweet.fields': 'created_at,author_id,context_annotations,conversation_id,public_metrics,referenced_tweets,reply_settings',
            'media.fields': 'duration_ms,height,media_key,preview_image_url,type,url,width,alt_text',
            'user.fields': 'created_at,description,entities,id,location,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified',
            'expansions': 'attachments.media_keys,attachments.poll_ids,author_id,entities.mentions.username,geo.place_id,in_reply_to_user_id,referenced_tweets.id,referenced_tweets.id.author_id'
        }
        
        headers = {
            'Authorization': f'Bearer {self.bearer_token}',
            'User-Agent': self._get_user_agent()
        }
        
        endpoint = f"{self.base_url}/tweets/search/recent"
        data = await self._fetch_json(endpoint, params=params, headers=headers)
        
        if not data or 'data' not in data:
            return results
        
        # Process includes for media and user info
        includes = data.get('includes', {})
        media_lookup = {m['media_key']: m for m in includes.get('media', [])}
        users_lookup = {u['id']: u for u in includes.get('users', [])}
        
        for tweet in data['data']:
            try:
                scan_result = await self._process_twitter_tweet(
                    tweet, query, media_lookup, users_lookup
                )
                if scan_result:
                    results.append(scan_result)
            except Exception as e:
                logger.error(f"Error processing Twitter tweet: {e}")
                continue
        
        return results
    
    async def _process_twitter_tweet(
        self,
        tweet: Dict[str, Any],
        query: str,
        media_lookup: Dict[str, Any],
        users_lookup: Dict[str, Any]
    ) -> Optional[ScanResult]:
        """Process individual Twitter tweet"""
        try:
            tweet_id = tweet.get('id')
            text = tweet.get('text', '')
            author_id = tweet.get('author_id')
            
            # Get author info
            author_info = users_lookup.get(author_id, {})
            author_username = author_info.get('username', '')
            author_name = author_info.get('name', '')
            
            # Build URL
            url = f"https://twitter.com/{author_username}/status/{tweet_id}" if author_username else f"https://twitter.com/i/status/{tweet_id}"
            
            # Extract media URLs
            media_urls = []
            image_url = None
            video_url = None
            
            attachments = tweet.get('attachments', {})
            if attachments.get('media_keys'):
                for media_key in attachments['media_keys']:
                    media = media_lookup.get(media_key, {})
                    
                    media_type = media.get('type')
                    if media_type == 'photo':
                        media_url = media.get('url')
                        if media_url:
                            media_urls.append(media_url)
                            if not image_url:
                                image_url = media_url
                    elif media_type in ['video', 'animated_gif']:
                        media_url = media.get('preview_image_url')
                        if media_url:
                            if not video_url:
                                video_url = media_url
                            media_urls.append(media_url)
            
            # Extract creation time
            created_at = None
            if tweet.get('created_at'):
                created_at = datetime.fromisoformat(
                    tweet['created_at'].replace('Z', '+00:00')
                )
            
            # Extract engagement stats
            public_metrics = tweet.get('public_metrics', {})
            engagement_stats = {
                'retweet_count': public_metrics.get('retweet_count', 0),
                'like_count': public_metrics.get('like_count', 0),
                'reply_count': public_metrics.get('reply_count', 0),
                'quote_count': public_metrics.get('quote_count', 0)
            }
            
            # Calculate confidence score
            confidence_score = self._calculate_twitter_relevance(tweet, text, query)
            
            # Build metadata
            metadata = {
                'tweet_id': tweet_id,
                'author_id': author_id,
                'conversation_id': tweet.get('conversation_id'),
                'lang': tweet.get('lang'),
                'reply_settings': tweet.get('reply_settings'),
                'context_annotations': tweet.get('context_annotations', []),
                'author_verified': author_info.get('verified', False),
                'author_followers': author_info.get('public_metrics', {}).get('followers_count', 0)
            }
            
            return ScanResult(
                url=url,
                platform="twitter",
                title=f"Tweet by @{author_username}",
                description=self._clean_text(text),
                image_url=image_url,
                video_url=video_url,
                thumbnail_url=image_url,  # Use image as thumbnail
                media_urls=media_urls,
                author=f"{author_name} (@{author_username})" if author_name else author_username,
                created_at=created_at,
                engagement_stats=engagement_stats,
                search_query=query,
                region=self.region.get('region_id') if self.region else None,
                confidence_score=confidence_score,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error processing Twitter tweet: {e}")
            return None
    
    def _calculate_twitter_relevance(
        self,
        tweet: Dict[str, Any],
        text: str,
        query: str
    ) -> float:
        """Calculate relevance score for Twitter tweet"""
        score = 0.5  # Base score
        
        query_terms = query.lower().split()
        text_lower = text.lower()
        
        # Score based on query term matches
        for term in query_terms:
            if term in text_lower:
                score += 0.3
        
        # Boost score for high engagement
        public_metrics = tweet.get('public_metrics', {})
        likes = public_metrics.get('like_count', 0)
        retweets = public_metrics.get('retweet_count', 0)
        
        if likes > 100:
            score += 0.2
        if retweets > 50:
            score += 0.1
        
        # Boost for tweets with media
        if tweet.get('attachments', {}).get('media_keys'):
            score += 0.2
        
        # Boost for leak-related terms
        leak_terms = ['leaked', 'leak', 'onlyfans', 'content', 'free']
        for term in leak_terms:
            if term in text_lower:
                score += 0.2
                break
        
        return min(score, 1.0)
    
    async def _fallback_search(self, query: str, limit: int) -> List[ScanResult]:
        """Fallback search using web scraping"""
        # Twitter heavily restricts web scraping
        # This would require more sophisticated techniques
        logger.warning("Twitter fallback search not implemented")
        return []
    
    async def health_check(self) -> bool:
        """Check if Twitter scanner is healthy"""
        try:
            if not self.bearer_token:
                return False
            
            # Test API access
            headers = {'Authorization': f'Bearer {self.bearer_token}'}
            response = await self._make_request(
                f"{self.base_url}/tweets/search/recent?query=test&max_results=10",
                headers=headers
            )
            return response is not None
        except Exception as e:
            logger.error(f"Twitter scanner health check failed: {e}")
            return False


class TikTokScanner(BaseScanner):
    """
    TikTok scanner for content discovery
    PRD: "Scans major platforms: TikTok"
    """
    
    def __init__(self, region: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(region=region, rate_limit=20, **kwargs)  # Very conservative
        
        # TikTok doesn't have a public API for search
        # We'll use web scraping with extreme caution due to anti-bot measures
        self.base_url = "https://www.tiktok.com"
        
    async def get_platform_name(self) -> str:
        return "tiktok"
    
    async def search(
        self,
        query: str,
        limit: int = 50,
        include_metadata: bool = True,
        **kwargs
    ) -> List[ScanResult]:
        """
        Search TikTok using web scraping
        Note: TikTok has strong anti-bot measures, results may be limited
        """
        results = []
        
        try:
            # Search hashtags
            hashtag_results = await self._search_hashtags(query, limit // 2)
            results.extend(hashtag_results)
            
            # Search users
            if len(results) < limit:
                user_results = await self._search_users(query, limit - len(results))
                results.extend(user_results)
                
        except Exception as e:
            logger.error(f"TikTok search error for query '{query}': {e}")
        
        logger.info(f"TikTok search found {len(results)} results for query: {query}")
        return results[:limit]
    
    async def _search_hashtags(self, query: str, limit: int) -> List[ScanResult]:
        """Search TikTok hashtags"""
        results = []
        
        try:
            # Create hashtag from query
            hashtag = re.sub(r'[^a-zA-Z0-9]', '', query.replace(' ', ''))
            
            # This is a placeholder implementation
            # Real implementation would require sophisticated anti-detection measures
            logger.info(f"TikTok hashtag search would target: #{hashtag}")
            
        except Exception as e:
            logger.error(f"Error searching TikTok hashtags: {e}")
        
        return results
    
    async def _search_users(self, query: str, limit: int) -> List[ScanResult]:
        """Search TikTok users"""
        results = []
        
        try:
            # Create username from query
            username = query.replace(' ', '').lower()
            
            # This is a placeholder implementation
            logger.info(f"TikTok user search would target: @{username}")
            
        except Exception as e:
            logger.error(f"Error searching TikTok users: {e}")
        
        return results
    
    async def health_check(self) -> bool:
        """Check if TikTok scanner is healthy"""
        try:
            # Simple connectivity test
            response = await self._make_request(self.base_url)
            return response is not None
        except Exception as e:
            logger.error(f"TikTok scanner health check failed: {e}")
            return False