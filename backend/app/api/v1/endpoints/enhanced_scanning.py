"""
Enhanced Scanning API Endpoints
Complete scanning engine API that integrates all scanning components
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.api.deps.auth import get_current_active_user as get_current_user
from app.services.scanning.orchestrator import orchestrator
from app.services.scanning.enhanced_search_engines import EnhancedSearchEngineScanner
from app.services.scanning.piracy_sites import PiracySiteDatabase

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/profiles/{profile_id}/scan/immediate")
async def trigger_immediate_scan(
    profile_id: int,
    profile_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """
    Trigger immediate priority scan for new user
    PRD: "Finds leaks immediately upon signup (within hours)"
    """
    try:
        # Schedule new user scan with highest priority
        scan_id = await orchestrator.schedule_new_user_scan(
            profile_id=profile_id,
            user_id=current_user.id,
            profile_data=profile_data
        )
        
        return {
            "scan_id": scan_id,
            "status": "scheduled",
            "priority": "urgent",
            "message": "New user scan scheduled - results within 2 hours",
            "estimated_completion": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error scheduling immediate scan: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule scan")


@router.post("/profiles/{profile_id}/scan/comprehensive")
async def trigger_comprehensive_scan(
    profile_id: int,
    profile_data: Dict[str, Any],
    platforms: Optional[List[str]] = None,
    regions: Optional[List[str]] = None,
    current_user = Depends(get_current_user)
):
    """
    Trigger comprehensive scan across all platforms and regions
    PRD: "Daily scans across 50+ country servers"
    """
    try:
        scan_id = await orchestrator.schedule_manual_scan(
            profile_id=profile_id,
            user_id=current_user.id,
            profile_data=profile_data,
            platforms=platforms
        )
        
        return {
            "scan_id": scan_id,
            "status": "scheduled",
            "priority": "high",
            "platforms": platforms or "all_platforms",
            "regions": regions or "optimal_selection",
            "message": "Comprehensive scan scheduled"
        }
        
    except Exception as e:
        logger.error(f"Error scheduling comprehensive scan: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule scan")


@router.get("/scans/{scan_id}/status")
async def get_scan_status(
    scan_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get real-time status of a running scan
    """
    try:
        status = await orchestrator.get_scan_status(scan_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        return {
            "scan_id": scan_id,
            "status": status.get("status", "unknown"),
            "progress": status.get("progress", 0),
            "created_at": status.get("created_at"),
            "started_at": status.get("started_at"),
            "completed_at": status.get("completed_at"),
            "results_summary": status.get("results", {}),
            "error": status.get("error")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scan status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scan status")


@router.get("/scans/{scan_id}/results")
async def get_scan_results(
    scan_id: str,
    limit: Optional[int] = Query(50, ge=1, le=500),
    offset: Optional[int] = Query(0, ge=0),
    min_confidence: Optional[float] = Query(0.5, ge=0.0, le=1.0),
    current_user = Depends(get_current_user)
):
    """
    Get detailed results from a completed scan
    """
    try:
        status = await orchestrator.get_scan_status(scan_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        if status.get("status") != "completed":
            return {
                "scan_id": scan_id,
                "status": status.get("status", "running"),
                "message": "Scan not yet completed",
                "partial_results_count": status.get("results", {}).get("total_matches_found", 0)
            }
        
        results = status.get("results", {})
        infringements = results.get("infringements", [])
        
        # Filter by confidence score
        filtered_infringements = [
            inf for inf in infringements 
            if inf.get("confidence", 0) >= min_confidence
        ]
        
        # Apply pagination
        paginated_results = filtered_infringements[offset:offset + limit]
        
        return {
            "scan_id": scan_id,
            "status": "completed",
            "total_results": len(filtered_infringements),
            "returned_results": len(paginated_results),
            "offset": offset,
            "limit": limit,
            "min_confidence": min_confidence,
            "scan_summary": {
                "urls_scanned": results.get("total_urls_scanned", 0),
                "matches_found": results.get("total_matches_found", 0),
                "platforms_scanned": results.get("platforms_scanned", []),
                "scan_duration_minutes": round(results.get("scan_duration_seconds", 0) / 60, 1)
            },
            "infringements": paginated_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scan results: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scan results")


@router.post("/search/targeted-leak-search")
async def targeted_leak_search(
    username: str,
    platforms: Optional[List[str]] = None,
    limit: Optional[int] = Query(50, ge=1, le=200),
    current_user = Depends(get_current_user)
):
    """
    Perform targeted search for leaked content across search engines
    """
    try:
        search_engine_scanner = EnhancedSearchEngineScanner()
        
        results = await search_engine_scanner.targeted_leak_search(
            username=username,
            platforms=platforms,
            limit=limit
        )
        
        # Group results by confidence level
        high_confidence = [r for r in results if r.confidence_score >= 0.8]
        medium_confidence = [r for r in results if 0.6 <= r.confidence_score < 0.8]
        low_confidence = [r for r in results if r.confidence_score < 0.6]
        
        return {
            "username": username,
            "total_results": len(results),
            "high_confidence_count": len(high_confidence),
            "medium_confidence_count": len(medium_confidence),
            "low_confidence_count": len(low_confidence),
            "results": {
                "high_confidence": high_confidence[:20],  # Top 20 high confidence
                "medium_confidence": medium_confidence[:15],  # Top 15 medium confidence
                "low_confidence": low_confidence[:10]  # Top 10 low confidence
            },
            "search_timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error in targeted leak search: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.post("/search/reverse-image")
async def reverse_image_search(
    image_urls: List[str],
    limit: Optional[int] = Query(25, ge=1, le=100),
    current_user = Depends(get_current_user)
):
    """
    Perform reverse image search to find where images appear online
    """
    try:
        if len(image_urls) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 image URLs allowed")
        
        search_engine_scanner = EnhancedSearchEngineScanner()
        
        results = await search_engine_scanner.reverse_image_search(
            image_urls=image_urls,
            limit=limit
        )
        
        # Group results by original image URL
        results_by_image = {}
        for result in results:
            original_query = result.search_query
            if original_query not in results_by_image:
                results_by_image[original_query] = []
            results_by_image[original_query].append(result)
        
        return {
            "searched_images": image_urls,
            "total_results": len(results),
            "results_by_image": results_by_image,
            "search_timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reverse image search: {e}")
        raise HTTPException(status_code=500, detail="Reverse image search failed")


@router.get("/piracy-sites/stats")
async def get_piracy_site_statistics(
    current_user = Depends(get_current_user)
):
    """
    Get statistics about known piracy sites in the database
    """
    try:
        piracy_db = PiracySiteDatabase()
        stats = {
            "database_stats": {
                "total_sites": len(piracy_db.sites),
                "active_sites": len(piracy_db.get_active_sites()),
                "high_risk_sites": len(piracy_db.get_high_risk_sites())
            },
            "sites_by_type": {
                site_type: len(piracy_db.get_sites_by_type(site_type))
                for site_type in ["forum", "leak_site", "tube_site", "telegram"]
            },
            "site_details": [
                {
                    "name": site.name,
                    "domain": site.domain,
                    "type": site.site_type,
                    "risk_level": site.risk_level,
                    "active": site.active,
                    "success_rate": round(site.success_rate, 2),
                    "last_scanned": site.last_scanned.isoformat() + "Z" if site.last_scanned else None
                }
                for site in piracy_db.get_active_sites()
            ]
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting piracy site stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.get("/orchestrator/stats")
async def get_orchestrator_statistics(
    current_user = Depends(get_current_user)
):
    """
    Get scanning orchestrator statistics and health
    """
    try:
        stats = await orchestrator.get_orchestrator_stats()
        
        return {
            "orchestrator_health": "healthy" if stats.get("active_scans", 0) >= 0 else "unhealthy",
            "infrastructure": {
                "active_scans": stats.get("active_scans", 0),
                "queue_size": stats.get("queue_size", 0),
                "total_regions": stats.get("total_regions", 0),
                "active_regions": stats.get("active_regions", 0),
                "total_platforms": stats.get("total_platforms", 0),
                "worker_count": stats.get("worker_count", 0)
            },
            "workers": stats.get("scan_workers", []),
            "capabilities": {
                "max_concurrent_scans": 20,
                "supported_platforms": [
                    "google", "bing", "reddit", "instagram", "twitter", 
                    "tiktok", "piracy_sites", "leak_forums"
                ],
                "global_regions": stats.get("active_regions", 0),
                "facial_recognition": True,
                "automated_dmca": True
            },
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error getting orchestrator stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get orchestrator statistics")


@router.post("/profiles/{profile_id}/scan/schedule-daily")
async def schedule_daily_scan(
    profile_id: int,
    profile_data: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """
    Schedule automated daily scan for a profile
    PRD: "Daily scans for infringements across web"
    """
    try:
        scan_id = await orchestrator.schedule_daily_scan(
            profile_id=profile_id,
            user_id=current_user.id,
            profile_data=profile_data
        )
        
        return {
            "scan_id": scan_id,
            "profile_id": profile_id,
            "status": "scheduled",
            "type": "daily_automated", 
            "next_scan": "Within 5 minutes (batched with other daily scans)",
            "message": "Daily scan scheduled successfully"
        }
        
    except Exception as e:
        logger.error(f"Error scheduling daily scan: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule daily scan")


@router.post("/test/platform-health")
async def test_platform_health(
    current_user = Depends(get_current_user)
):
    """
    Test health of all scanning platforms
    """
    try:
        from app.services.scanning.platforms import (
            GoogleScanner, RedditScanner, InstagramScanner, 
            TwitterScanner, TikTokScanner
        )
        from app.services.scanning.piracy_sites import PiracySiteScanner
        
        platforms = {
            "google": GoogleScanner(),
            "reddit": RedditScanner(),
            "instagram": InstagramScanner(), 
            "twitter": TwitterScanner(),
            "tiktok": TikTokScanner(),
            "piracy_sites": PiracySiteScanner()
        }
        
        health_results = {}
        
        for platform_name, platform_scanner in platforms.items():
            try:
                async with platform_scanner:
                    is_healthy = await platform_scanner.health_check()
                    health_results[platform_name] = {
                        "status": "healthy" if is_healthy else "unhealthy",
                        "tested_at": datetime.utcnow().isoformat() + "Z"
                    }
            except Exception as e:
                health_results[platform_name] = {
                    "status": "error",
                    "error": str(e),
                    "tested_at": datetime.utcnow().isoformat() + "Z"
                }
        
        overall_health = "healthy" if all(
            result.get("status") == "healthy" 
            for result in health_results.values()
        ) else "degraded"
        
        return {
            "overall_status": overall_health,
            "platforms": health_results,
            "test_timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error testing platform health: {e}")
        raise HTTPException(status_code=500, detail="Platform health test failed")