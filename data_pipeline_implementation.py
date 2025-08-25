#!/usr/bin/env python3
"""
Real-Time Content Monitoring Data Pipeline Implementation
Production-ready implementation for DMCA automation at scale
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import json
import hashlib
import time
from dataclasses import dataclass
from contextlib import asynccontextmanager

# Core dependencies
import redis.asyncio as redis
import asyncpg
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import clickhouse_connect
from minio import Minio
import boto3
from elasticsearch import AsyncElasticsearch

# ML and content processing
import numpy as np
import cv2
from PIL import Image
import imagehash
from sentence_transformers import SentenceTransformer

# API clients
import aiohttp
from googleapiclient.discovery import build
import instaloader
import TikTokApi

# Configuration
from pydantic import BaseSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PipelineConfig(BaseSettings):
    """Configuration for data pipeline"""
    
    # Database connections
    POSTGRES_URL: str = "postgresql://user:pass@localhost:5432/autodmca"
    CLICKHOUSE_URL: str = "clickhouse://localhost:8123/autodmca"
    REDIS_URL: str = "redis://localhost:6379"
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    
    # Kafka configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_SECURITY_PROTOCOL: str = "PLAINTEXT"
    
    # Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    
    # API keys (should be loaded from secure storage)
    YOUTUBE_API_KEY: str = ""
    INSTAGRAM_ACCESS_TOKEN: str = ""
    TIKTOK_API_KEY: str = ""
    
    # Pipeline settings
    BATCH_SIZE: int = 100
    MAX_CONCURRENT_REQUESTS: int = 10
    SIMILARITY_THRESHOLD: float = 0.85
    FINGERPRINT_DIMENSIONS: int = 512
    
    class Config:
        env_file = ".env"


@dataclass
class ContentItem:
    """Standardized content item structure"""
    platform: str
    content_id: str
    url: str
    title: str
    description: str
    creator_id: str
    creator_name: str
    published_at: datetime
    thumbnail_url: Optional[str] = None
    view_count: int = 0
    like_count: int = 0
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    fingerprints: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if self.fingerprints is None:
            self.fingerprints = {}


class APIQuotaManager:
    """Intelligent API quota and rate limiting management"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.quota_configs = {
            'youtube': {
                'daily_quota': 10000,
                'requests_per_second': 10,
                'burst_capacity': 50,
                'cost_per_request': 1  # quota units
            },
            'instagram': {
                'hourly_quota': 200,
                'requests_per_second': 2,
                'burst_capacity': 10,
                'cost_per_request': 1
            },
            'tiktok': {
                'daily_quota': 1000,
                'requests_per_second': 1,
                'burst_capacity': 5,
                'cost_per_request': 1
            }
        }
    
    async def acquire_request_token(self, platform: str, cost: int = 1) -> bool:
        """Acquire tokens for API request with specified cost"""
        config = self.quota_configs.get(platform)
        if not config:
            return False
        
        current_time = time.time()
        
        # Check daily quota
        quota_key = f"quota:{platform}:{datetime.now().strftime('%Y-%m-%d')}"
        current_usage = int(await self.redis.get(quota_key) or 0)
        
        if current_usage + cost > config['daily_quota']:
            logger.warning(f"Daily quota exceeded for {platform}: {current_usage}/{config['daily_quota']}")
            return False
        
        # Token bucket rate limiting
        bucket_key = f"bucket:{platform}"
        pipe = self.redis.pipeline()
        pipe.multi()
        
        # Get current bucket state
        bucket_data = await self.redis.hmget(bucket_key, 'tokens', 'last_refill')
        tokens = int(bucket_data[0] or config['burst_capacity'])
        last_refill = float(bucket_data[1] or current_time)
        
        # Calculate token refill
        time_elapsed = current_time - last_refill
        tokens_to_add = int(time_elapsed * config['requests_per_second'])
        tokens = min(tokens + tokens_to_add, config['burst_capacity'])
        
        if tokens >= cost:
            # Consume tokens
            tokens -= cost
            
            # Update bucket state
            await self.redis.hset(bucket_key, mapping={
                'tokens': tokens,
                'last_refill': current_time
            })
            
            # Update quota usage
            await self.redis.incrby(quota_key, cost)
            await self.redis.expire(quota_key, 86400)  # 24 hours
            
            return True
        
        logger.debug(f"Rate limit hit for {platform}: {tokens} tokens available, {cost} needed")
        return False
    
    async def get_quota_status(self, platform: str) -> Dict[str, Any]:
        """Get current quota and rate limit status"""
        config = self.quota_configs.get(platform, {})
        quota_key = f"quota:{platform}:{datetime.now().strftime('%Y-%m-%d')}"
        bucket_key = f"bucket:{platform}"
        
        current_usage = int(await self.redis.get(quota_key) or 0)
        bucket_data = await self.redis.hmget(bucket_key, 'tokens')
        available_tokens = int(bucket_data[0] or config.get('burst_capacity', 0))
        
        return {
            'platform': platform,
            'daily_quota': config.get('daily_quota', 0),
            'current_usage': current_usage,
            'remaining_quota': config.get('daily_quota', 0) - current_usage,
            'available_tokens': available_tokens,
            'utilization_percent': (current_usage / max(config.get('daily_quota', 1), 1)) * 100
        }


class ContentFingerprintService:
    """Advanced content fingerprinting using multiple techniques"""
    
    def __init__(self):
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.image_hash_size = 16
        
    async def generate_fingerprints(self, content_item: ContentItem) -> Dict[str, Any]:
        """Generate multiple types of fingerprints for content"""
        fingerprints = {}
        
        # Text fingerprints
        if content_item.title or content_item.description:
            text_content = f"{content_item.title or ''} {content_item.description or ''}"
            fingerprints.update(await self._generate_text_fingerprints(text_content))
        
        # Image fingerprints
        if content_item.thumbnail_url:
            image_fingerprints = await self._generate_image_fingerprints(content_item.thumbnail_url)
            fingerprints.update(image_fingerprints)
        
        # Metadata fingerprints
        metadata_fingerprints = self._generate_metadata_fingerprints(content_item)
        fingerprints.update(metadata_fingerprints)
        
        return fingerprints
    
    async def _generate_text_fingerprints(self, text: str) -> Dict[str, Any]:
        """Generate text-based fingerprints"""
        fingerprints = {}
        
        # Semantic embedding
        embedding = self.sentence_model.encode(text)
        fingerprints['text_embedding'] = embedding.tolist()
        
        # Simple hash for exact matches
        fingerprints['text_hash'] = hashlib.sha256(text.lower().strip().encode()).hexdigest()
        
        # N-gram hashes for fuzzy matching
        words = text.lower().split()
        if len(words) >= 3:
            trigrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
            fingerprints['trigram_hashes'] = [
                hashlib.md5(trigram.encode()).hexdigest() for trigram in trigrams
            ]
        
        return fingerprints
    
    async def _generate_image_fingerprints(self, image_url: str) -> Dict[str, Any]:
        """Generate image-based fingerprints"""
        fingerprints = {}
        
        try:
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        
                        # Convert to PIL Image
                        image = Image.open(io.BytesIO(image_data))
                        
                        # Perceptual hashes
                        fingerprints['phash'] = str(imagehash.phash(image, hash_size=self.image_hash_size))
                        fingerprints['dhash'] = str(imagehash.dhash(image, hash_size=self.image_hash_size))
                        fingerprints['ahash'] = str(imagehash.average_hash(image, hash_size=self.image_hash_size))
                        fingerprints['whash'] = str(imagehash.whash(image, hash_size=self.image_hash_size))
                        
                        # Color histogram
                        color_histogram = self._calculate_color_histogram(image)
                        fingerprints['color_histogram'] = color_histogram.tolist()
                        
        except Exception as e:
            logger.error(f"Failed to generate image fingerprints for {image_url}: {e}")
        
        return fingerprints
    
    def _calculate_color_histogram(self, image: Image.Image, bins: int = 32) -> np.ndarray:
        """Calculate color histogram for image similarity"""
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize for consistency
        image = image.resize((256, 256))
        
        # Calculate histogram for each channel
        hist_r = np.histogram(np.array(image)[:,:,0], bins=bins, range=(0, 256))[0]
        hist_g = np.histogram(np.array(image)[:,:,1], bins=bins, range=(0, 256))[0]
        hist_b = np.histogram(np.array(image)[:,:,2], bins=bins, range=(0, 256))[0]
        
        # Combine histograms
        combined_hist = np.concatenate([hist_r, hist_g, hist_b])
        
        # Normalize
        return combined_hist / np.sum(combined_hist)
    
    def _generate_metadata_fingerprints(self, content_item: ContentItem) -> Dict[str, Any]:
        """Generate fingerprints from metadata"""
        fingerprints = {}
        
        # Creator fingerprint
        creator_info = f"{content_item.creator_id}:{content_item.creator_name}".lower()
        fingerprints['creator_hash'] = hashlib.md5(creator_info.encode()).hexdigest()
        
        # Tags fingerprint
        if content_item.tags:
            tags_str = ','.join(sorted(tag.lower() for tag in content_item.tags))
            fingerprints['tags_hash'] = hashlib.md5(tags_str.encode()).hexdigest()
        
        # Temporal fingerprint (publication time bucket)
        if content_item.published_at:
            # Group by hour for temporal clustering
            hour_bucket = content_item.published_at.replace(minute=0, second=0, microsecond=0)
            fingerprints['temporal_bucket'] = hour_bucket.isoformat()
        
        return fingerprints


class YouTubeDataExtractor:
    """YouTube API data extraction with intelligent quota management"""
    
    def __init__(self, api_key: str, quota_manager: APIQuotaManager):
        self.api_key = api_key
        self.quota_manager = quota_manager
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        
    async def search_content(self, search_terms: List[str], max_results: int = 50) -> List[ContentItem]:
        """Search for content using YouTube API"""
        content_items = []
        
        for term in search_terms:
            # Check quota before making request
            if not await self.quota_manager.acquire_request_token('youtube', cost=100):
                logger.warning(f"YouTube quota exhausted, skipping search for: {term}")
                continue
            
            try:
                # Search for videos
                search_response = self.youtube.search().list(
                    part='id,snippet',
                    q=term,
                    type='video',
                    maxResults=min(max_results, 50),
                    order='relevance'
                ).execute()
                
                video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
                
                if video_ids:
                    # Get detailed video information
                    videos = await self._get_video_details(video_ids)
                    content_items.extend(videos)
                    
                logger.info(f"Retrieved {len(video_ids)} videos for term: {term}")
                
            except Exception as e:
                logger.error(f"Error searching YouTube for '{term}': {e}")
        
        return content_items
    
    async def _get_video_details(self, video_ids: List[str]) -> List[ContentItem]:
        """Get detailed information for videos"""
        content_items = []
        
        # Check quota (1 unit per video)
        if not await self.quota_manager.acquire_request_token('youtube', cost=len(video_ids)):
            logger.warning("Insufficient YouTube quota for video details")
            return content_items
        
        try:
            videos_response = self.youtube.videos().list(
                part='id,snippet,statistics,contentDetails',
                id=','.join(video_ids)
            ).execute()
            
            for video in videos_response.get('items', []):
                snippet = video.get('snippet', {})
                statistics = video.get('statistics', {})
                
                content_item = ContentItem(
                    platform='youtube',
                    content_id=video['id'],
                    url=f"https://www.youtube.com/watch?v={video['id']}",
                    title=snippet.get('title', ''),
                    description=snippet.get('description', ''),
                    creator_id=snippet.get('channelId', ''),
                    creator_name=snippet.get('channelTitle', ''),
                    published_at=datetime.fromisoformat(snippet.get('publishedAt', '').replace('Z', '+00:00')),
                    thumbnail_url=snippet.get('thumbnails', {}).get('high', {}).get('url'),
                    view_count=int(statistics.get('viewCount', 0)),
                    like_count=int(statistics.get('likeCount', 0)),
                    tags=snippet.get('tags', []),
                    metadata={
                        'duration': video.get('contentDetails', {}).get('duration'),
                        'category_id': snippet.get('categoryId'),
                        'default_language': snippet.get('defaultLanguage'),
                        'comment_count': int(statistics.get('commentCount', 0))
                    }
                )
                
                content_items.append(content_item)
                
        except Exception as e:
            logger.error(f"Error getting YouTube video details: {e}")
        
        return content_items


class InstagramDataExtractor:
    """Instagram data extraction with rate limiting"""
    
    def __init__(self, access_token: str, quota_manager: APIQuotaManager):
        self.access_token = access_token
        self.quota_manager = quota_manager
        self.loader = instaloader.Instaloader()
        
    async def search_hashtags(self, hashtags: List[str], max_posts: int = 50) -> List[ContentItem]:
        """Search Instagram content by hashtags"""
        content_items = []
        
        for hashtag in hashtags:
            if not await self.quota_manager.acquire_request_token('instagram'):
                logger.warning(f"Instagram quota exhausted, skipping hashtag: {hashtag}")
                continue
            
            try:
                posts = self.loader.get_hashtag_posts(hashtag)
                count = 0
                
                for post in posts:
                    if count >= max_posts:
                        break
                    
                    content_item = ContentItem(
                        platform='instagram',
                        content_id=post.shortcode,
                        url=f"https://www.instagram.com/p/{post.shortcode}/",
                        title=post.caption or '',
                        description=post.caption or '',
                        creator_id=post.owner_username,
                        creator_name=post.owner_username,
                        published_at=post.date,
                        thumbnail_url=post.url,
                        view_count=post.video_view_count if post.is_video else 0,
                        like_count=post.likes,
                        tags=post.caption_hashtags,
                        metadata={
                            'is_video': post.is_video,
                            'comment_count': post.comments,
                            'location': post.location.name if post.location else None
                        }
                    )
                    
                    content_items.append(content_item)
                    count += 1
                    
                logger.info(f"Retrieved {count} posts for hashtag: #{hashtag}")
                
            except Exception as e:
                logger.error(f"Error searching Instagram hashtag #{hashtag}: {e}")
        
        return content_items


class SimilarityMatcher:
    """Advanced content similarity matching using multiple algorithms"""
    
    def __init__(self, elasticsearch_client: AsyncElasticsearch):
        self.es = elasticsearch_client
        self.similarity_threshold = 0.85
        
    async def find_matches(self, content_item: ContentItem, fingerprints: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find similar content using various matching techniques"""
        matches = []
        
        # Text embedding similarity search
        if 'text_embedding' in fingerprints:
            text_matches = await self._search_text_embeddings(
                fingerprints['text_embedding'], 
                content_item
            )
            matches.extend(text_matches)
        
        # Image perceptual hash matching
        image_hash_fields = ['phash', 'dhash', 'ahash', 'whash']
        for hash_field in image_hash_fields:
            if hash_field in fingerprints:
                image_matches = await self._search_image_hashes(
                    hash_field,
                    fingerprints[hash_field],
                    content_item
                )
                matches.extend(image_matches)
        
        # Color histogram similarity
        if 'color_histogram' in fingerprints:
            color_matches = await self._search_color_histograms(
                fingerprints['color_histogram'],
                content_item
            )
            matches.extend(color_matches)
        
        # Exact hash matches
        if 'text_hash' in fingerprints:
            exact_matches = await self._search_exact_hashes(
                fingerprints['text_hash'],
                content_item
            )
            matches.extend(exact_matches)
        
        # Deduplicate and rank matches
        unique_matches = self._deduplicate_matches(matches)
        ranked_matches = sorted(unique_matches, key=lambda x: x['confidence'], reverse=True)
        
        return [match for match in ranked_matches if match['confidence'] >= self.similarity_threshold]
    
    async def _search_text_embeddings(self, embedding: List[float], content_item: ContentItem) -> List[Dict[str, Any]]:
        """Search for similar text embeddings"""
        try:
            query = {
                "query": {
                    "knn": {
                        "text_embedding": {
                            "vector": embedding,
                            "k": 20
                        }
                    }
                },
                "_source": ["content_id", "creator_id", "platform", "url", "title"]
            }
            
            response = await self.es.search(
                index="content_fingerprints",
                body=query
            )
            
            matches = []
            for hit in response['hits']['hits']:
                if hit['_score'] >= 0.8:  # Elasticsearch similarity score
                    matches.append({
                        'content_id': content_item.content_id,
                        'match_id': hit['_source']['content_id'],
                        'match_creator_id': hit['_source']['creator_id'],
                        'match_platform': hit['_source']['platform'],
                        'match_url': hit['_source']['url'],
                        'match_title': hit['_source']['title'],
                        'confidence': min(hit['_score'], 1.0),
                        'match_type': 'text_embedding',
                        'original_platform': content_item.platform,
                        'original_url': content_item.url
                    })
            
            return matches
            
        except Exception as e:
            logger.error(f"Error in text embedding search: {e}")
            return []
    
    async def _search_image_hashes(self, hash_field: str, hash_value: str, content_item: ContentItem) -> List[Dict[str, Any]]:
        """Search for similar image hashes with Hamming distance"""
        try:
            # Elasticsearch script for Hamming distance calculation
            script = {
                "script": {
                    "source": """
                    String target = params.target_hash;
                    String candidate = doc[params.field].value;
                    if (candidate == null) return 0;
                    
                    int distance = 0;
                    int minLength = Math.min(target.length(), candidate.length());
                    for (int i = 0; i < minLength; i++) {
                        if (target.charAt(i) != candidate.charAt(i)) {
                            distance++;
                        }
                    }
                    distance += Math.abs(target.length() - candidate.length());
                    
                    // Convert to similarity score (max hamming distance for 64-bit hash is 64)
                    return Math.max(0, (64.0 - distance) / 64.0);
                    """,
                    "params": {
                        "target_hash": hash_value,
                        "field": hash_field
                    }
                }
            }
            
            query = {
                "query": {
                    "function_score": {
                        "query": {"match_all": {}},
                        "script_score": script
                    }
                },
                "min_score": 0.85,  # Only return good matches
                "_source": ["content_id", "creator_id", "platform", "url", "title"]
            }
            
            response = await self.es.search(
                index="content_fingerprints",
                body=query
            )
            
            matches = []
            for hit in response['hits']['hits']:
                matches.append({
                    'content_id': content_item.content_id,
                    'match_id': hit['_source']['content_id'],
                    'match_creator_id': hit['_source']['creator_id'],
                    'match_platform': hit['_source']['platform'],
                    'match_url': hit['_source']['url'],
                    'match_title': hit['_source']['title'],
                    'confidence': hit['_score'],
                    'match_type': f'image_{hash_field}',
                    'original_platform': content_item.platform,
                    'original_url': content_item.url
                })
            
            return matches
            
        except Exception as e:
            logger.error(f"Error in image hash search for {hash_field}: {e}")
            return []
    
    def _deduplicate_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate matches and keep highest confidence"""
        seen = {}
        
        for match in matches:
            key = f"{match['match_id']}:{match['match_creator_id']}"
            
            if key not in seen or match['confidence'] > seen[key]['confidence']:
                seen[key] = match
        
        return list(seen.values())


class StreamProcessor:
    """Real-time stream processing using Kafka"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.producer = KafkaProducer(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: str(k).encode('utf-8'),
            acks='all',
            retries=3
        )
        
    async def stream_content(self, topic: str, content_items: List[ContentItem]):
        """Stream content items to Kafka topic"""
        for item in content_items:
            try:
                # Convert to dict for JSON serialization
                item_dict = {
                    'platform': item.platform,
                    'content_id': item.content_id,
                    'url': item.url,
                    'title': item.title,
                    'description': item.description,
                    'creator_id': item.creator_id,
                    'creator_name': item.creator_name,
                    'published_at': item.published_at.isoformat(),
                    'thumbnail_url': item.thumbnail_url,
                    'view_count': item.view_count,
                    'like_count': item.like_count,
                    'tags': item.tags,
                    'metadata': item.metadata,
                    'fingerprints': item.fingerprints,
                    'processed_at': datetime.utcnow().isoformat()
                }
                
                # Use content_id as partition key for ordering
                self.producer.send(
                    topic,
                    key=item.content_id,
                    value=item_dict
                )
                
            except Exception as e:
                logger.error(f"Error streaming content item {item.content_id}: {e}")
        
        # Ensure all messages are sent
        self.producer.flush()
    
    async def stream_matches(self, topic: str, matches: List[Dict[str, Any]]):
        """Stream content matches to Kafka topic"""
        for match in matches:
            try:
                match['detected_at'] = datetime.utcnow().isoformat()
                
                self.producer.send(
                    topic,
                    key=match['content_id'],
                    value=match
                )
                
            except Exception as e:
                logger.error(f"Error streaming match: {e}")
        
        self.producer.flush()


class ContentMonitoringPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.redis_client = None
        self.postgres_client = None
        self.clickhouse_client = None
        self.elasticsearch_client = None
        
        # Initialize components
        self.quota_manager = None
        self.fingerprint_service = ContentFingerprintService()
        self.stream_processor = StreamProcessor(config)
        
        # Platform extractors
        self.youtube_extractor = None
        self.instagram_extractor = None
        self.similarity_matcher = None
        
    async def initialize(self):
        """Initialize all pipeline components"""
        # Database connections
        self.redis_client = redis.from_url(self.config.REDIS_URL)
        self.postgres_client = await asyncpg.connect(self.config.POSTGRES_URL)
        self.clickhouse_client = clickhouse_connect.get_async_client(
            host=self.config.CLICKHOUSE_URL.split('//')[1].split(':')[0]
        )
        self.elasticsearch_client = AsyncElasticsearch([self.config.ELASTICSEARCH_URL])
        
        # Initialize managers
        self.quota_manager = APIQuotaManager(self.redis_client)
        
        # Initialize extractors
        if self.config.YOUTUBE_API_KEY:
            self.youtube_extractor = YouTubeDataExtractor(
                self.config.YOUTUBE_API_KEY,
                self.quota_manager
            )
        
        if self.config.INSTAGRAM_ACCESS_TOKEN:
            self.instagram_extractor = InstagramDataExtractor(
                self.config.INSTAGRAM_ACCESS_TOKEN,
                self.quota_manager
            )
        
        self.similarity_matcher = SimilarityMatcher(self.elasticsearch_client)
        
        logger.info("Content monitoring pipeline initialized")
    
    async def run_extraction_cycle(self, search_terms: List[str], hashtags: List[str]):
        """Run a complete extraction and processing cycle"""
        all_content_items = []
        
        # YouTube extraction
        if self.youtube_extractor:
            logger.info("Starting YouTube content extraction")
            youtube_content = await self.youtube_extractor.search_content(search_terms)
            all_content_items.extend(youtube_content)
            logger.info(f"Extracted {len(youtube_content)} YouTube items")
        
        # Instagram extraction
        if self.instagram_extractor:
            logger.info("Starting Instagram content extraction")
            instagram_content = await self.instagram_extractor.search_hashtags(hashtags)
            all_content_items.extend(instagram_content)
            logger.info(f"Extracted {len(instagram_content)} Instagram items")
        
        # Process content in batches
        batch_size = self.config.BATCH_SIZE
        for i in range(0, len(all_content_items), batch_size):
            batch = all_content_items[i:i + batch_size]
            await self._process_content_batch(batch)
            
        logger.info(f"Completed extraction cycle: {len(all_content_items)} total items")
    
    async def _process_content_batch(self, content_items: List[ContentItem]):
        """Process a batch of content items"""
        # Generate fingerprints
        for item in content_items:
            fingerprints = await self.fingerprint_service.generate_fingerprints(item)
            item.fingerprints = fingerprints
        
        # Stream raw content to Kafka
        await self.stream_processor.stream_content("content.raw", content_items)
        
        # Find similarity matches
        all_matches = []
        for item in content_items:
            if item.fingerprints:
                matches = await self.similarity_matcher.find_matches(item, item.fingerprints)
                all_matches.extend(matches)
        
        # Stream matches to processing queue
        if all_matches:
            await self.stream_processor.stream_matches("content.matches", all_matches)
            logger.info(f"Found {len(all_matches)} potential matches in batch")
        
        # Store in databases
        await self._store_content_batch(content_items, all_matches)
    
    async def _store_content_batch(self, content_items: List[ContentItem], matches: List[Dict[str, Any]]):
        """Store processed content and matches in databases"""
        # Store in PostgreSQL for transactional operations
        content_data = []
        fingerprint_data = []
        
        for item in content_items:
            content_data.append({
                'platform': item.platform,
                'content_id': item.content_id,
                'url': item.url,
                'title': item.title,
                'description': item.description,
                'creator_id': item.creator_id,
                'creator_name': item.creator_name,
                'published_at': item.published_at,
                'view_count': item.view_count,
                'like_count': item.like_count,
                'tags': json.dumps(item.tags),
                'metadata': json.dumps(item.metadata)
            })
            
            # Prepare fingerprint data for Elasticsearch
            if item.fingerprints:
                fingerprint_doc = {
                    'content_id': item.content_id,
                    'platform': item.platform,
                    'url': item.url,
                    'title': item.title,
                    'creator_id': item.creator_id,
                    **item.fingerprints  # Include all fingerprint fields
                }
                fingerprint_data.append(fingerprint_doc)
        
        # Batch insert into PostgreSQL
        if content_data:
            await self._batch_insert_postgres(content_data)
        
        # Batch index in Elasticsearch
        if fingerprint_data:
            await self._batch_index_elasticsearch(fingerprint_data)
        
        # Store matches in ClickHouse for analytics
        if matches:
            await self._store_matches_clickhouse(matches)
        
        logger.info(f"Stored {len(content_data)} content items and {len(matches)} matches")
    
    async def _batch_insert_postgres(self, content_data: List[Dict[str, Any]]):
        """Batch insert content data into PostgreSQL"""
        query = """
        INSERT INTO content_items (
            platform, content_id, url, title, description, creator_id, 
            creator_name, published_at, view_count, like_count, tags, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (platform, content_id) DO UPDATE SET
            view_count = EXCLUDED.view_count,
            like_count = EXCLUDED.like_count,
            updated_at = NOW()
        """
        
        batch_data = [
            (
                item['platform'], item['content_id'], item['url'], item['title'],
                item['description'], item['creator_id'], item['creator_name'],
                item['published_at'], item['view_count'], item['like_count'],
                item['tags'], item['metadata']
            )
            for item in content_data
        ]
        
        await self.postgres_client.executemany(query, batch_data)
    
    async def _batch_index_elasticsearch(self, fingerprint_data: List[Dict[str, Any]]):
        """Batch index fingerprint data in Elasticsearch"""
        actions = []
        
        for doc in fingerprint_data:
            action = {
                "_index": "content_fingerprints",
                "_id": doc['content_id'],
                "_source": doc
            }
            actions.append(action)
        
        # Use bulk API for efficient indexing
        from elasticsearch.helpers import async_bulk
        await async_bulk(self.elasticsearch_client, actions)
    
    async def _store_matches_clickhouse(self, matches: List[Dict[str, Any]]):
        """Store matches in ClickHouse for analytics"""
        if not matches:
            return
            
        # Prepare data for ClickHouse insertion
        match_data = []
        for match in matches:
            match_data.append([
                datetime.utcnow(),  # event_time
                match['content_id'],
                match['match_id'],
                match['original_platform'],
                match['match_platform'],
                match['confidence'],
                match['match_type'],
                match['original_url'],
                match['match_url'],
                json.dumps(match)  # full match data as JSON
            ])
        
        query = """
        INSERT INTO content_matches_events (
            event_time, content_id, match_id, original_platform, match_platform,
            confidence, match_type, original_url, match_url, metadata
        ) VALUES
        """
        
        await self.clickhouse_client.insert(
            'content_matches_events',
            match_data,
            column_names=[
                'event_time', 'content_id', 'match_id', 'original_platform', 
                'match_platform', 'confidence', 'match_type', 'original_url', 
                'match_url', 'metadata'
            ]
        )
    
    async def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get comprehensive pipeline metrics"""
        metrics = {}
        
        # Quota status for all platforms
        platforms = ['youtube', 'instagram', 'tiktok']
        quota_status = {}
        
        for platform in platforms:
            quota_status[platform] = await self.quota_manager.get_quota_status(platform)
        
        metrics['quota_status'] = quota_status
        
        # Content processing metrics from ClickHouse
        content_metrics_query = """
        SELECT 
            original_platform,
            COUNT(*) as total_matches,
            AVG(confidence) as avg_confidence,
            COUNT(DISTINCT content_id) as unique_content_items
        FROM content_matches_events
        WHERE event_time >= now() - INTERVAL 24 HOUR
        GROUP BY original_platform
        """
        
        content_metrics = await self.clickhouse_client.query(content_metrics_query)
        metrics['content_metrics'] = content_metrics.result_rows
        
        # PostgreSQL metrics
        postgres_metrics_query = """
        SELECT 
            platform,
            COUNT(*) as total_items,
            COUNT(DISTINCT creator_id) as unique_creators,
            MAX(created_at) as last_processed
        FROM content_items
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY platform
        """
        
        postgres_result = await self.postgres_client.fetch(postgres_metrics_query)
        metrics['postgres_metrics'] = [dict(row) for row in postgres_result]
        
        return metrics
    
    async def cleanup(self):
        """Cleanup pipeline resources"""
        if self.redis_client:
            await self.redis_client.close()
        if self.postgres_client:
            await self.postgres_client.close()
        if self.clickhouse_client:
            await self.clickhouse_client.close()
        if self.elasticsearch_client:
            await self.elasticsearch_client.close()
        if self.producer:
            self.producer.close()
        
        logger.info("Pipeline cleanup completed")


async def main():
    """Main pipeline execution function"""
    config = PipelineConfig()
    pipeline = ContentMonitoringPipeline(config)
    
    try:
        # Initialize pipeline
        await pipeline.initialize()
        
        # Define search terms and hashtags for monitoring
        search_terms = [
            "leaked content",
            "onlyfans leak",
            "premium content free",
        ]
        
        hashtags = [
            "leaks",
            "onlyfansleak", 
            "freecontent"
        ]
        
        # Run extraction cycle
        await pipeline.run_extraction_cycle(search_terms, hashtags)
        
        # Get and log metrics
        metrics = await pipeline.get_pipeline_metrics()
        logger.info(f"Pipeline metrics: {json.dumps(metrics, indent=2, default=str)}")
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise
    finally:
        await pipeline.cleanup()


if __name__ == "__main__":
    asyncio.run(main())