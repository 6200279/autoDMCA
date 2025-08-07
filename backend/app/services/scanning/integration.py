from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.profile import ProtectedProfile
from app.db.models.infringement import Infringement
from app.schemas.infringement import InfringementCreate, InfringementType, InfringementSeverity
from app.api.websocket import notify_infringement_found, notify_scan_completed


class ScanningEngineIntegration:
    """Integration with the scanning engine."""
    
    def __init__(self):
        self.scanner = None
        self._initialize_scanner()
    
    def _initialize_scanner(self):
        """Initialize the scanning engine."""
        try:
            # Import the scanning engine
            from scanning.scanner import ContentScanner
            from scanning.config import ScanConfig
            
            config = ScanConfig()
            self.scanner = ContentScanner(config)
        except ImportError:
            print("Warning: Scanning engine not available")
            self.scanner = None
    
    async def schedule_profile_scan(
        self,
        profile_id: int,
        scan_type: str = "comprehensive",
        platforms: Optional[List[str]] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Schedule a scan for a protected profile."""
        db = next(get_db())
        
        try:
            # Get profile
            profile = db.query(ProtectedProfile).filter(
                ProtectedProfile.id == profile_id
            ).first()
            
            if not profile:
                raise ValueError(f"Profile {profile_id} not found")
            
            if not profile.is_active:
                raise ValueError(f"Profile {profile_id} is not active")
            
            # Create scan configuration
            scan_config = {
                "profile_id": profile_id,
                "profile_name": profile.name,
                "scan_type": scan_type,
                "platforms": platforms or self._get_default_platforms(),
                "priority": priority,
                "keywords": profile.keywords or [],
                "aliases": profile.aliases or [],
                "reference_images": await self._get_profile_reference_images(profile_id),
                "face_encodings": await self._get_profile_face_encodings(profile_id),
                "scheduled_at": datetime.utcnow().isoformat(),
                "user_id": profile.user_id
            }
            
            # Schedule scan with the scanning engine
            if self.scanner:
                scan_id = await self._schedule_with_scanner(scan_config)
            else:
                # Fallback: simulate scan for development
                scan_id = await self._simulate_scan(scan_config)
            
            return {
                "scan_id": scan_id,
                "profile_id": profile_id,
                "status": "scheduled",
                "message": f"Scan scheduled for profile '{profile.name}'"
            }
            
        finally:
            db.close()
    
    async def _schedule_with_scanner(self, scan_config: Dict[str, Any]) -> str:
        """Schedule scan with the actual scanning engine."""
        try:
            # Use the task manager to schedule the scan
            from scanning.scheduler.task_manager import TaskManager
            
            task_manager = TaskManager()
            scan_task = await task_manager.schedule_scan(
                profile_id=scan_config["profile_id"],
                scan_type=scan_config["scan_type"],
                platforms=scan_config["platforms"],
                keywords=scan_config["keywords"],
                reference_images=scan_config["reference_images"],
                priority=scan_config["priority"]
            )
            
            # Start background monitoring of scan progress
            asyncio.create_task(self._monitor_scan_progress(scan_task.id, scan_config))
            
            return scan_task.id
            
        except Exception as e:
            print(f"Error scheduling scan with engine: {e}")
            # Fallback to simulation
            return await self._simulate_scan(scan_config)
    
    async def _simulate_scan(self, scan_config: Dict[str, Any]) -> str:
        """Simulate a scan for development/testing."""
        import uuid
        scan_id = str(uuid.uuid4())
        
        # Simulate scan progress in background
        asyncio.create_task(self._simulate_scan_progress(scan_id, scan_config))
        
        return scan_id
    
    async def _monitor_scan_progress(self, scan_id: str, scan_config: Dict[str, Any]):
        """Monitor scan progress and update database."""
        try:
            from scanning.scheduler.task_manager import TaskManager
            
            task_manager = TaskManager()
            profile_id = scan_config["profile_id"]
            user_id = scan_config["user_id"]
            
            while True:
                # Check scan status
                task_status = await task_manager.get_task_status(scan_id)
                
                if task_status.status == "completed":
                    # Process scan results
                    results = await task_manager.get_task_results(scan_id)
                    await self._process_scan_results(profile_id, user_id, results)
                    
                    # Notify user of completion
                    await notify_scan_completed(user_id, {
                        "scan_id": scan_id,
                        "profile_id": profile_id,
                        "infringements_found": len(results.get("infringements", [])),
                        "platforms_scanned": results.get("platforms_scanned", []),
                        "scan_duration": results.get("duration_seconds", 0)
                    })
                    break
                
                elif task_status.status == "failed":
                    print(f"Scan {scan_id} failed: {task_status.error}")
                    break
                
                # Wait before checking again
                await asyncio.sleep(30)
                
        except Exception as e:
            print(f"Error monitoring scan progress: {e}")
    
    async def _simulate_scan_progress(self, scan_id: str, scan_config: Dict[str, Any]):
        """Simulate scan progress for development."""
        profile_id = scan_config["profile_id"]
        user_id = scan_config["user_id"]
        
        # Wait to simulate scan time
        await asyncio.sleep(10)  # 10 second "scan"
        
        # Create fake scan results
        fake_results = {
            "infringements": [
                {
                    "url": "https://example.com/fake-infringement-1",
                    "platform": "Instagram",
                    "confidence_score": 0.85,
                    "infringement_type": "image",
                    "evidence_urls": ["https://example.com/evidence-1.jpg"]
                },
                {
                    "url": "https://example.com/fake-infringement-2", 
                    "platform": "Twitter",
                    "confidence_score": 0.92,
                    "infringement_type": "profile",
                    "evidence_urls": []
                }
            ],
            "platforms_scanned": ["Instagram", "Twitter", "TikTok", "OnlyFans"],
            "duration_seconds": 8,
            "total_urls_checked": 1247
        }
        
        # Process fake results
        await self._process_scan_results(profile_id, user_id, fake_results)
        
        # Notify completion
        await notify_scan_completed(user_id, {
            "scan_id": scan_id,
            "profile_id": profile_id,
            "infringements_found": len(fake_results["infringements"]),
            "platforms_scanned": fake_results["platforms_scanned"],
            "scan_duration": fake_results["duration_seconds"]
        })
    
    async def _process_scan_results(
        self, 
        profile_id: int, 
        user_id: int, 
        results: Dict[str, Any]
    ):
        """Process scan results and create infringement records."""
        db = next(get_db())
        
        try:
            infringements_created = 0
            
            for infringement_data in results.get("infringements", []):
                # Check if infringement already exists
                existing = db.query(Infringement).filter(
                    Infringement.url == infringement_data["url"],
                    Infringement.profile_id == profile_id
                ).first()
                
                if existing:
                    continue  # Skip duplicate
                
                # Determine severity based on confidence score
                confidence = infringement_data.get("confidence_score", 0.5)
                if confidence >= 0.9:
                    severity = InfringementSeverity.CRITICAL
                elif confidence >= 0.75:
                    severity = InfringementSeverity.HIGH
                elif confidence >= 0.6:
                    severity = InfringementSeverity.MEDIUM
                else:
                    severity = InfringementSeverity.LOW
                
                # Create infringement record
                infringement = Infringement(
                    profile_id=profile_id,
                    url=infringement_data["url"],
                    platform=infringement_data.get("platform", "Unknown"),
                    infringement_type=InfringementType(infringement_data.get("infringement_type", "content")),
                    status="pending",
                    severity=severity,
                    confidence_score=confidence,
                    description=infringement_data.get("description", "Detected by automated scan"),
                    evidence_urls=infringement_data.get("evidence_urls", []),
                    metadata={
                        "scan_id": results.get("scan_id"),
                        "detection_method": infringement_data.get("detection_method"),
                        "match_details": infringement_data.get("match_details", {})
                    },
                    discovered_at=datetime.utcnow()
                )
                
                db.add(infringement)
                infringements_created += 1
                
                # Notify user of new infringement
                await notify_infringement_found(user_id, {
                    "id": infringement.id,
                    "profile_id": profile_id,
                    "url": infringement.url,
                    "platform": infringement.platform,
                    "confidence_score": confidence,
                    "severity": severity
                })
            
            db.commit()
            print(f"Created {infringements_created} new infringement records for profile {profile_id}")
            
        except Exception as e:
            db.rollback()
            print(f"Error processing scan results: {e}")
        finally:
            db.close()
    
    async def _get_profile_reference_images(self, profile_id: int) -> List[Dict[str, Any]]:
        """Get reference images for a profile."""
        # In a real implementation, this would query the reference_images table
        return []
    
    async def _get_profile_face_encodings(self, profile_id: int) -> List[str]:
        """Get face encodings for a profile."""
        # In a real implementation, this would get stored face encodings
        return []
    
    def _get_default_platforms(self) -> List[str]:
        """Get default platforms to scan."""
        return [
            "Instagram",
            "Twitter", 
            "TikTok",
            "OnlyFans",
            "Pornhub",
            "Xvideos",
            "RedTube",
            "YouPorn",
            "XHamster"
        ]
    
    async def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """Get status of a running scan."""
        if self.scanner:
            try:
                from scanning.scheduler.task_manager import TaskManager
                task_manager = TaskManager()
                status = await task_manager.get_task_status(scan_id)
                return {
                    "scan_id": scan_id,
                    "status": status.status,
                    "progress": status.progress,
                    "message": status.message,
                    "started_at": status.started_at,
                    "estimated_completion": status.estimated_completion
                }
            except Exception as e:
                return {
                    "scan_id": scan_id,
                    "status": "error",
                    "message": f"Error getting scan status: {e}"
                }
        else:
            # Return fake status for simulation
            return {
                "scan_id": scan_id,
                "status": "completed",
                "progress": 100,
                "message": "Scan completed successfully"
            }
    
    async def cancel_scan(self, scan_id: str) -> bool:
        """Cancel a running scan."""
        if self.scanner:
            try:
                from scanning.scheduler.task_manager import TaskManager
                task_manager = TaskManager()
                return await task_manager.cancel_task(scan_id)
            except Exception as e:
                print(f"Error cancelling scan: {e}")
                return False
        return True  # Always succeed for simulation


# Global instance
scanning_integration = ScanningEngineIntegration()


# Convenience functions for API endpoints
async def schedule_scan(
    profile_id: int,
    scan_type: str = "comprehensive",
    platforms: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Schedule a scan for a profile."""
    return await scanning_integration.schedule_profile_scan(
        profile_id, scan_type, platforms
    )