"""
Optimized Scanning API Endpoints
High-performance endpoints using all optimization techniques
"""
import asyncio
import time
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.services.ai.optimized_content_matcher import OptimizedContentMatcher
from app.services.scanning.optimized_web_crawler import OptimizedWebCrawler
from app.services.cache.multi_level_cache import cache_manager, cached
from app.services.monitoring.performance_monitor import performance_monitor, track_performance
from app.services.database.query_optimizer import db_optimizer

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize optimized services
content_matcher = OptimizedContentMatcher()
web_crawler = OptimizedWebCrawler()


class ProfileScanRequest(BaseModel):
    """Request model for profile scanning"""
    profile_data: Dict[str, Any] = Field(..., description="Profile information for scanning")
    max_urls: int = Field(default=100, ge=1, le=500, description="Maximum URLs to scan")
    deep_scan: bool = Field(default=False, description="Enable deep scanning")
    priority_only: bool = Field(default=False, description="Scan only high-priority sites")
    enable_caching: bool = Field(default=True, description="Enable result caching")


class BatchAnalysisRequest(BaseModel):
    """Request model for batch content analysis"""
    content_items: List[Dict[str, Any]] = Field(..., description="Content items to analyze")
    profile_data: Dict[str, Any] = Field(..., description="Profile data for matching")
    batch_size: int = Field(default=8, ge=1, le=32, description="Processing batch size")


class ScanResponse(BaseModel):
    """Response model for scanning operations"""
    scan_id: str
    status: str
    results_count: int
    processing_time_ms: float
    cache_performance: Dict[str, Any]
    ai_performance: Dict[str, Any]
    matches_found: int
    high_confidence_matches: int
    recommendations: List[str]


class BatchAnalysisResponse(BaseModel):
    """Response model for batch analysis"""
    analysis_id: str
    total_items: int
    processed_items: int
    total_matches: int
    processing_time_ms: float
    batch_metrics: Dict[str, Any]
    results: List[Dict[str, Any]]


@router.post("/scan-profile-optimized", response_model=ScanResponse)
@track_performance(endpoint="optimized_scan")
async def scan_profile_optimized(
    request: ProfileScanRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Optimized profile scanning with advanced performance features
    
    Features:
    - Batch processing for improved throughput
    - Multi-level caching for faster responses
    - Intelligent URL prioritization
    - Real-time performance monitoring
    - Background result processing
    """
    start_time = time.time()
    scan_id = f"scan_{int(time.time())}_{hashlib.md5(str(request.profile_data).encode()).hexdigest()[:8]}"
    
    try:
        # Input validation
        if not request.profile_data.get('username'):
            raise HTTPException(status_code=400, detail="Username is required in profile_data")
        
        # Check cache first if enabled
        cache_key = None
        if request.enable_caching:
            cache_key = f"profile_scan:{hashlib.md5(str(request.dict()).encode()).hexdigest()}"
            cached_result = await cache_manager.get(cache_key, cache_type="scan_result")
            
            if cached_result:
                logger.info(f"Cache hit for scan: {scan_id}")
                cached_result['scan_id'] = scan_id
                cached_result['cache_performance']['cache_hit'] = True
                return JSONResponse(content=cached_result)
        
        # Initialize services if needed
        if not hasattr(content_matcher, 'redis_client') or content_matcher.redis_client is None:
            await content_matcher.initialize()
        
        if not hasattr(web_crawler, 'session') or web_crawler.session is None:
            await web_crawler.initialize()
        
        # Execute optimized scan
        scan_results = await web_crawler.scan_for_profile_optimized(
            profile_data=request.profile_data,
            max_urls=request.max_urls,
            deep_scan=request.deep_scan,
            priority_only=request.priority_only
        )
        
        # Analyze matches and confidence levels
        total_matches = 0
        high_confidence_matches = 0
        
        for result in scan_results:
            matches = result.metadata.get('content_matches', [])
            total_matches += len(matches)
            high_confidence_matches += len([m for m in matches if m.get('confidence', 0) > 0.8])
        
        # Generate recommendations
        recommendations = await _generate_scan_recommendations(scan_results, request.profile_data)
        
        # Get performance metrics
        ai_metrics = await content_matcher.get_performance_metrics()
        crawler_metrics = await web_crawler.get_crawler_metrics()
        cache_stats = await cache_manager.get_stats()
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        # Prepare response
        response_data = {
            'scan_id': scan_id,
            'status': 'completed',
            'results_count': len(scan_results),
            'processing_time_ms': processing_time,
            'cache_performance': {
                'cache_hit': False,
                'l1_hit_rate': cache_stats['l1_memory']['hit_rate'],
                'l2_hit_rate': cache_stats['l2_redis']['hit_rate'],
                'total_cache_hit_rate': cache_stats['overall']['hit_rate']
            },
            'ai_performance': {
                'average_inference_time_ms': ai_metrics['average_processing_time_ms'],
                'cache_hit_rate': ai_metrics.get('cache_hit_rate', 0.0),
                'gpu_memory_usage_gb': ai_metrics['gpu_memory_usage_gb'],
                'batch_size_used': ai_metrics['batch_size']
            },
            'matches_found': total_matches,
            'high_confidence_matches': high_confidence_matches,
            'recommendations': recommendations,
            'crawler_metrics': {
                'urls_processed': crawler_metrics['total_urls_processed'],
                'success_rate': crawler_metrics['success_rate'],
                'avg_response_time_ms': crawler_metrics['average_response_time_ms'],
                'cache_hit_rate': crawler_metrics['cache_hit_rate']
            },
            'detailed_results': [
                {
                    'url': result.url,
                    'status': result.status,
                    'matches': result.metadata.get('content_matches', []),
                    'processing_time_ms': result.processing_time_ms,
                    'cache_hit': result.cache_hit
                }
                for result in scan_results[:20]  # Limit detailed results
            ]
        }
        
        # Cache successful results
        if request.enable_caching and cache_key:
            await cache_manager.set(
                cache_key,
                response_data,
                ttl=1800,  # 30 minutes
                cache_type="scan_result"
            )
        
        # Store results in database (background task)
        background_tasks.add_task(
            _store_scan_results,
            scan_id,
            request.profile_data,
            scan_results,
            processing_time
        )
        
        # Track performance metrics
        performance_monitor.track_ai_inference(
            model_name="profile_scanner",
            inference_time_ms=processing_time,
            batch_size=len(scan_results),
            memory_usage_mb=ai_metrics.get('memory_usage_mb', 0),
            error=False
        )
        
        logger.info(
            f"Scan {scan_id} completed: {len(scan_results)} results, "
            f"{total_matches} matches in {processing_time:.2f}ms"
        )
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Scan error for {scan_id}: {e}")
        
        # Track error
        performance_monitor.track_ai_inference(
            model_name="profile_scanner",
            inference_time_ms=(time.time() - start_time) * 1000,
            batch_size=0,
            error=True
        )
        
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.post("/analyze-content-batch", response_model=BatchAnalysisResponse)
@track_performance(endpoint="batch_analysis")
async def analyze_content_batch(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Batch content analysis with optimized AI processing
    
    Features:
    - Batch processing for improved GPU utilization
    - Intelligent batching based on content type
    - Memory-efficient processing
    - Advanced caching strategies
    """
    start_time = time.time()
    analysis_id = f"batch_{int(time.time())}_{len(request.content_items)}"
    
    try:
        # Validate input
        if not request.content_items:
            raise HTTPException(status_code=400, detail="No content items provided")
        
        if len(request.content_items) > 100:
            raise HTTPException(status_code=400, detail="Batch size too large (max 100)")
        
        # Initialize content matcher if needed
        if not hasattr(content_matcher, 'redis_client') or content_matcher.redis_client is None:
            await content_matcher.initialize()
        
        # Prepare content items for batch processing
        content_batch = []
        for i, item in enumerate(request.content_items):
            content_url = item.get('url', f'batch_item_{i}')
            content_data = item.get('data', b'')
            
            # Convert data if it's base64 encoded
            if isinstance(content_data, str):
                import base64
                try:
                    content_data = base64.b64decode(content_data)
                except Exception:
                    content_data = content_data.encode('utf-8')
            
            content_batch.append((content_url, content_data, request.profile_data))
        
        # Execute batch analysis
        batch_results = await content_matcher.analyze_content_batch(content_batch)
        
        # Process results
        total_matches = 0
        processed_results = []
        
        for i, matches in enumerate(batch_results):
            item_result = {
                'item_index': i,
                'url': content_batch[i][0],
                'matches_count': len(matches),
                'matches': [
                    {
                        'type': match.match_type,
                        'confidence': match.confidence,
                        'metadata': match.metadata,
                        'processing_time_ms': match.processing_time_ms
                    }
                    for match in matches
                ],
                'high_confidence_matches': len([m for m in matches if m.confidence > 0.8])
            }
            
            processed_results.append(item_result)
            total_matches += len(matches)
        
        # Get batch performance metrics
        ai_metrics = await content_matcher.get_performance_metrics()
        processing_time = (time.time() - start_time) * 1000
        
        # Prepare response
        response_data = {
            'analysis_id': analysis_id,
            'total_items': len(request.content_items),
            'processed_items': len(processed_results),
            'total_matches': total_matches,
            'processing_time_ms': processing_time,
            'batch_metrics': {
                'avg_processing_time_per_item_ms': processing_time / len(request.content_items),
                'ai_inference_time_ms': ai_metrics['average_processing_time_ms'],
                'cache_hit_rate': ai_metrics.get('cache_hit_rate', 0.0),
                'gpu_utilization': ai_metrics['gpu_memory_usage_gb'] > 0,
                'batch_efficiency': len(request.content_items) / max(1, processing_time / 1000)  # items per second
            },
            'results': processed_results
        }
        
        # Store batch results (background task)
        background_tasks.add_task(
            _store_batch_analysis_results,
            analysis_id,
            request.profile_data,
            batch_results,
            processing_time
        )
        
        # Track performance
        performance_monitor.track_ai_inference(
            model_name="batch_analyzer",
            inference_time_ms=processing_time,
            batch_size=len(request.content_items),
            memory_usage_mb=ai_metrics.get('memory_usage_mb', 0),
            error=False
        )
        
        logger.info(
            f"Batch analysis {analysis_id} completed: {len(request.content_items)} items, "
            f"{total_matches} matches in {processing_time:.2f}ms"
        )
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Batch analysis error for {analysis_id}: {e}")
        
        performance_monitor.track_ai_inference(
            model_name="batch_analyzer",
            inference_time_ms=(time.time() - start_time) * 1000,
            batch_size=len(request.content_items) if request.content_items else 0,
            error=True
        )
        
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@router.post("/upload-and-analyze")
@track_performance(endpoint="upload_analysis")
async def upload_and_analyze_content(
    files: List[UploadFile] = File(...),
    profile_data: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Upload and analyze multiple files with optimized processing
    """
    start_time = time.time()
    
    try:
        # Parse profile data
        import json
        profile_dict = json.loads(profile_data)
        
        # Validate file count
        if len(files) > 20:
            raise HTTPException(status_code=400, detail="Too many files (max 20)")
        
        # Process files in batch
        content_items = []
        for i, file in enumerate(files):
            # Validate file size
            content = await file.read()
            if len(content) > 10 * 1024 * 1024:  # 10MB limit
                raise HTTPException(status_code=400, detail=f"File {file.filename} too large")
            
            content_items.append((file.filename or f"upload_{i}", content, profile_dict))
        
        # Initialize content matcher
        if not hasattr(content_matcher, 'redis_client') or content_matcher.redis_client is None:
            await content_matcher.initialize()
        
        # Analyze batch
        results = await content_matcher.analyze_content_batch(content_items)
        
        # Process results
        analysis_results = []
        total_matches = 0
        
        for i, matches in enumerate(results):
            filename = files[i].filename or f"upload_{i}"
            file_result = {
                'filename': filename,
                'file_size_bytes': len(content_items[i][1]),
                'matches_count': len(matches),
                'matches': [
                    {
                        'type': match.match_type,
                        'confidence': match.confidence,
                        'metadata': match.metadata
                    }
                    for match in matches
                ]
            }
            analysis_results.append(file_result)
            total_matches += len(matches)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Store results in background
        background_tasks.add_task(
            _store_upload_analysis_results,
            profile_dict,
            analysis_results,
            processing_time
        )
        
        return {
            'status': 'completed',
            'files_processed': len(files),
            'total_matches': total_matches,
            'processing_time_ms': processing_time,
            'results': analysis_results
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid profile_data JSON")
    except Exception as e:
        logger.error(f"Upload analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/performance-metrics")
async def get_performance_metrics():
    """Get comprehensive performance metrics"""
    
    try:
        # Get metrics from all services
        ai_metrics = await content_matcher.get_performance_metrics()
        crawler_metrics = await web_crawler.get_crawler_metrics()
        cache_stats = await cache_manager.get_stats()
        db_metrics = await db_optimizer.get_query_performance_report()
        system_metrics = await performance_monitor.get_performance_summary()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'ai_performance': ai_metrics,
            'crawler_performance': crawler_metrics,
            'cache_performance': cache_stats,
            'database_performance': db_metrics,
            'system_performance': system_metrics,
            'sla_compliance': {
                'ai_inference_sla': ai_metrics['average_processing_time_ms'] < 2000,
                'api_response_sla': system_metrics['performance']['response_time_p95_ms'] < 500,
                'cache_performance_sla': cache_stats['overall']['hit_rate'] > 0.7,
                'overall_health': 'healthy' if all([
                    ai_metrics['average_processing_time_ms'] < 2000,
                    system_metrics['performance']['response_time_p95_ms'] < 500,
                    cache_stats['overall']['hit_rate'] > 0.7
                ]) else 'degraded'
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")


@router.get("/health-check")
async def optimized_health_check():
    """Comprehensive health check with performance validation"""
    
    start_time = time.time()
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'response_time_ms': 0.0,
        'services': {},
        'performance_indicators': {}
    }
    
    try:
        # Check AI service
        try:
            ai_metrics = await content_matcher.get_performance_metrics()
            health_status['services']['ai_matcher'] = {
                'status': 'healthy',
                'average_processing_time_ms': ai_metrics['average_processing_time_ms'],
                'cache_hit_rate': ai_metrics.get('cache_hit_rate', 0.0)
            }
        except Exception as e:
            health_status['services']['ai_matcher'] = {'status': 'unhealthy', 'error': str(e)}
            health_status['status'] = 'degraded'
        
        # Check web crawler
        try:
            crawler_metrics = await web_crawler.get_crawler_metrics()
            health_status['services']['web_crawler'] = {
                'status': 'healthy',
                'success_rate': crawler_metrics['success_rate'],
                'cache_hit_rate': crawler_metrics['cache_hit_rate']
            }
        except Exception as e:
            health_status['services']['web_crawler'] = {'status': 'unhealthy', 'error': str(e)}
            health_status['status'] = 'degraded'
        
        # Check cache system
        try:
            cache_stats = await cache_manager.get_stats()
            health_status['services']['cache_system'] = {
                'status': 'healthy',
                'hit_rate': cache_stats['overall']['hit_rate'],
                'l1_memory_usage': cache_stats['l1_memory']['memory_usage_mb'],
                'redis_connected': cache_stats['l2_redis']['connected']
            }
        except Exception as e:
            health_status['services']['cache_system'] = {'status': 'unhealthy', 'error': str(e)}
            health_status['status'] = 'degraded'
        
        # Check database
        try:
            db_metrics = await db_optimizer.get_query_performance_report()
            health_status['services']['database'] = {
                'status': 'healthy',
                'avg_query_time_ms': db_metrics['summary']['avg_execution_time_ms'],
                'slow_queries': db_metrics['summary']['slow_query_count']
            }
        except Exception as e:
            health_status['services']['database'] = {'status': 'unhealthy', 'error': str(e)}
            health_status['status'] = 'degraded'
        
        # Performance indicators
        health_status['performance_indicators'] = {
            'ai_inference_under_2s': health_status['services'].get('ai_matcher', {}).get('average_processing_time_ms', 9999) < 2000,
            'cache_hit_rate_above_70': health_status['services'].get('cache_system', {}).get('hit_rate', 0) > 0.7,
            'crawler_success_rate_above_90': health_status['services'].get('web_crawler', {}).get('success_rate', 0) > 90,
            'database_performance_good': health_status['services'].get('database', {}).get('avg_query_time_ms', 9999) < 1000
        }
        
        # Overall health determination
        unhealthy_services = [name for name, service in health_status['services'].items() if service.get('status') != 'healthy']
        if unhealthy_services:
            health_status['status'] = 'unhealthy' if len(unhealthy_services) > 1 else 'degraded'
            health_status['unhealthy_services'] = unhealthy_services
        
        health_status['response_time_ms'] = (time.time() - start_time) * 1000
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'response_time_ms': (time.time() - start_time) * 1000,
            'error': str(e)
        }


# Helper functions for background tasks
async def _store_scan_results(
    scan_id: str,
    profile_data: Dict[str, Any],
    scan_results: List[Any],
    processing_time: float
):
    """Store scan results in database"""
    try:
        async with db_optimizer.get_session('write') as session:
            # Store scan record
            from sqlalchemy import text
            insert_query = text("""
                INSERT INTO scan_results (scan_id, profile_data, results_count, processing_time_ms, created_at)
                VALUES (:scan_id, :profile_data, :results_count, :processing_time_ms, :created_at)
            """)
            
            await session.execute(insert_query, {
                'scan_id': scan_id,
                'profile_data': json.dumps(profile_data),
                'results_count': len(scan_results),
                'processing_time_ms': processing_time,
                'created_at': datetime.utcnow()
            })
            
        logger.info(f"Stored scan results for {scan_id}")
        
    except Exception as e:
        logger.error(f"Failed to store scan results: {e}")


async def _store_batch_analysis_results(
    analysis_id: str,
    profile_data: Dict[str, Any],
    batch_results: List[Any],
    processing_time: float
):
    """Store batch analysis results in database"""
    try:
        async with db_optimizer.get_session('write') as session:
            from sqlalchemy import text
            insert_query = text("""
                INSERT INTO batch_analysis_results (analysis_id, profile_data, batch_size, processing_time_ms, created_at)
                VALUES (:analysis_id, :profile_data, :batch_size, :processing_time_ms, :created_at)
            """)
            
            await session.execute(insert_query, {
                'analysis_id': analysis_id,
                'profile_data': json.dumps(profile_data),
                'batch_size': len(batch_results),
                'processing_time_ms': processing_time,
                'created_at': datetime.utcnow()
            })
            
        logger.info(f"Stored batch analysis results for {analysis_id}")
        
    except Exception as e:
        logger.error(f"Failed to store batch analysis results: {e}")


async def _store_upload_analysis_results(
    profile_data: Dict[str, Any],
    analysis_results: List[Dict[str, Any]],
    processing_time: float
):
    """Store upload analysis results in database"""
    try:
        async with db_optimizer.get_session('write') as session:
            from sqlalchemy import text
            insert_query = text("""
                INSERT INTO upload_analysis_results (profile_data, files_count, processing_time_ms, created_at)
                VALUES (:profile_data, :files_count, :processing_time_ms, :created_at)
            """)
            
            await session.execute(insert_query, {
                'profile_data': json.dumps(profile_data),
                'files_count': len(analysis_results),
                'processing_time_ms': processing_time,
                'created_at': datetime.utcnow()
            })
            
        logger.info(f"Stored upload analysis results")
        
    except Exception as e:
        logger.error(f"Failed to store upload analysis results: {e}")


async def _generate_scan_recommendations(
    scan_results: List[Any],
    profile_data: Dict[str, Any]
) -> List[str]:
    """Generate optimization recommendations based on scan results"""
    recommendations = []
    
    if not scan_results:
        recommendations.append("No results found - consider expanding search parameters")
        return recommendations
    
    # Analyze scan performance
    successful_scans = [r for r in scan_results if r.status == 'completed']
    failed_scans = [r for r in scan_results if r.status == 'failed']
    cached_scans = [r for r in scan_results if r.cache_hit]
    
    success_rate = len(successful_scans) / len(scan_results) * 100 if scan_results else 0
    cache_hit_rate = len(cached_scans) / len(scan_results) * 100 if scan_results else 0
    
    # Performance recommendations
    if success_rate < 80:
        recommendations.append(f"Low success rate ({success_rate:.1f}%) - consider adjusting crawler settings")
    
    if cache_hit_rate < 30:
        recommendations.append(f"Low cache hit rate ({cache_hit_rate:.1f}%) - results will improve with repeated scans")
    
    # Content recommendations
    total_matches = sum(len(r.metadata.get('content_matches', [])) for r in successful_scans)
    if total_matches == 0:
        recommendations.append("No matches found - consider adding more keywords or expanding scan scope")
    elif total_matches > 50:
        recommendations.append("Many matches found - consider creating DMCA takedown requests")
    
    # Site-specific recommendations
    reddit_results = [r for r in successful_scans if 'reddit.com' in r.url]
    if reddit_results and any(r.metadata.get('content_matches') for r in reddit_results):
        recommendations.append("Reddit matches found - consider monitoring specific subreddits")
    
    return recommendations


import json