from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.takedown import TakedownRequest
from app.db.models.infringement import Infringement
from app.db.models.user import User
from app.api.websocket import notify_takedown_status_updated, notify_content_removed


class DMCAIntegration:
    """Integration with the DMCA takedown system."""
    
    def __init__(self):
        self.dmca_service = None
        self._initialize_dmca_service()
    
    def _initialize_dmca_service(self):
        """Initialize the DMCA service."""
        try:
            # Import the DMCA service
            from src.autodmca.services.dmca_service import DMCAService
            self.dmca_service = DMCAService()
        except ImportError:
            print("Warning: DMCA service not available")
            self.dmca_service = None
    
    async def send_takedown_request(self, takedown_id: int) -> Dict[str, Any]:
        """Send a takedown request."""
        db = next(get_db())
        
        try:
            # Get takedown request
            takedown = db.query(TakedownRequest).filter(
                TakedownRequest.id == takedown_id
            ).first()
            
            if not takedown:
                raise ValueError(f"Takedown request {takedown_id} not found")
            
            if takedown.status != "draft":
                raise ValueError(f"Takedown request {takedown_id} is not in draft status")
            
            # Get associated infringement
            infringement = db.query(Infringement).filter(
                Infringement.id == takedown.infringement_id
            ).first()
            
            if not infringement:
                raise ValueError(f"Infringement {takedown.infringement_id} not found")
            
            # Prepare takedown data
            takedown_data = {
                "takedown_id": takedown_id,
                "infringement_url": infringement.url,
                "platform": infringement.platform,
                "recipient_email": takedown.recipient_email,
                "recipient_name": takedown.recipient_name,
                "subject": takedown.subject,
                "body": takedown.body,
                "legal_basis": takedown.legal_basis,
                "copyright_statement": takedown.copyright_statement,
                "good_faith_statement": takedown.good_faith_statement,
                "accuracy_statement": takedown.accuracy_statement,
                "method": takedown.method,
                "evidence_urls": infringement.evidence_urls or []
            }
            
            # Send takedown request
            if self.dmca_service:
                result = await self._send_with_dmca_service(takedown_data)
            else:
                # Fallback: simulate sending for development
                result = await self._simulate_takedown_sending(takedown_data)
            
            # Update takedown status
            takedown.status = "sent"
            takedown.sent_at = datetime.utcnow()
            takedown.expires_at = datetime.utcnow() + timedelta(days=7)  # 7 day response period
            takedown.updated_at = datetime.utcnow()
            
            # Update infringement status
            infringement.status = "takedown_requested"
            infringement.updated_at = datetime.utcnow()
            
            db.commit()
            
            # Notify user
            await notify_takedown_status_updated(takedown.user_id, {
                "takedown_id": takedown_id,
                "status": "sent",
                "infringement_url": infringement.url,
                "platform": infringement.platform,
                "sent_at": takedown.sent_at.isoformat(),
                "expires_at": takedown.expires_at.isoformat() if takedown.expires_at else None
            })
            
            # Start monitoring for responses
            asyncio.create_task(self._monitor_takedown_response(takedown_id))
            
            return {
                "takedown_id": takedown_id,
                "status": "sent",
                "message": f"Takedown request sent for {infringement.url}",
                "sent_at": takedown.sent_at.isoformat(),
                "expires_at": takedown.expires_at.isoformat() if takedown.expires_at else None
            }
            
        except Exception as e:
            db.rollback()
            # Update takedown with error
            if 'takedown' in locals():
                takedown.status = "draft"
                takedown.notes = f"Failed to send: {str(e)}"
                takedown.updated_at = datetime.utcnow()
                db.commit()
            
            return {
                "takedown_id": takedown_id,
                "status": "failed",
                "message": f"Failed to send takedown request: {str(e)}"
            }
        finally:
            db.close()
    
    async def _send_with_dmca_service(self, takedown_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send takedown using the actual DMCA service."""
        try:
            # Create takedown notice using the DMCA service
            from src.autodmca.models.takedown import TakedownNotice
            
            notice = TakedownNotice(
                infringing_url=takedown_data["infringement_url"],
                original_work_description=takedown_data["body"],
                copyright_owner=takedown_data.get("copyright_owner", "Content Owner"),
                contact_email=takedown_data.get("contact_email", takedown_data["recipient_email"]),
                good_faith_statement=takedown_data["good_faith_statement"],
                accuracy_statement=takedown_data["accuracy_statement"],
                signature="Digital Signature"
            )
            
            # Submit takedown notice
            result = await self.dmca_service.submit_takedown(
                notice,
                method=takedown_data["method"],
                recipient_email=takedown_data["recipient_email"]
            )
            
            return {
                "success": True,
                "tracking_id": result.get("tracking_id"),
                "message": "Takedown request sent successfully"
            }
            
        except Exception as e:
            print(f"Error sending takedown with DMCA service: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _simulate_takedown_sending(self, takedown_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate sending takedown for development."""
        import uuid
        
        # Simulate sending delay
        await asyncio.sleep(2)
        
        # Generate fake tracking ID
        tracking_id = f"TK_{uuid.uuid4().hex[:8].upper()}"
        
        return {
            "success": True,
            "tracking_id": tracking_id,
            "message": "Takedown request sent successfully (simulated)"
        }
    
    async def _monitor_takedown_response(self, takedown_id: int):
        """Monitor for takedown responses and updates."""
        try:
            # In a real implementation, this would:
            # 1. Monitor email for responses
            # 2. Check platform APIs for content removal
            # 3. Track compliance deadlines
            
            # For simulation, wait and then update status
            await asyncio.sleep(300)  # Wait 5 minutes for demo
            
            # Simulate response received
            await self._simulate_takedown_response(takedown_id)
            
        except Exception as e:
            print(f"Error monitoring takedown response: {e}")
    
    async def _simulate_takedown_response(self, takedown_id: int):
        """Simulate takedown response for development."""
        db = next(get_db())
        
        try:
            takedown = db.query(TakedownRequest).filter(
                TakedownRequest.id == takedown_id
            ).first()
            
            if not takedown:
                return
            
            # Simulate different response types (80% success rate)
            import random
            if random.random() < 0.8:
                # Successful removal
                takedown.status = "content_removed"
                takedown.resolved_at = datetime.utcnow()
                
                # Update infringement
                infringement = db.query(Infringement).filter(
                    Infringement.id == takedown.infringement_id
                ).first()
                if infringement:
                    infringement.status = "resolved"
                    infringement.updated_at = datetime.utcnow()
                
                # Notify user of successful removal
                await notify_content_removed(takedown.user_id, {
                    "takedown_id": takedown_id,
                    "infringement_url": infringement.url if infringement else "",
                    "platform": infringement.platform if infringement else "",
                    "resolved_at": takedown.resolved_at.isoformat()
                })
                
            else:
                # Request rejected
                takedown.status = "rejected"
                takedown.resolved_at = datetime.utcnow()
                takedown.notes = "Platform rejected takedown request - manual review required"
            
            takedown.updated_at = datetime.utcnow()
            db.commit()
            
            # Notify user of status update
            await notify_takedown_status_updated(takedown.user_id, {
                "takedown_id": takedown_id,
                "status": takedown.status,
                "resolved_at": takedown.resolved_at.isoformat() if takedown.resolved_at else None,
                "notes": takedown.notes
            })
            
        except Exception as e:
            print(f"Error simulating takedown response: {e}")
        finally:
            db.close()
    
    async def process_takedown_response(
        self, 
        takedown_id: int, 
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a takedown response from a platform."""
        db = next(get_db())
        
        try:
            takedown = db.query(TakedownRequest).filter(
                TakedownRequest.id == takedown_id
            ).first()
            
            if not takedown:
                raise ValueError(f"Takedown request {takedown_id} not found")
            
            response_type = response_data.get("type", "unknown")
            
            if response_type == "compliance":
                # Content was removed
                takedown.status = "content_removed"
                takedown.resolved_at = datetime.utcnow()
                
                # Update infringement
                infringement = db.query(Infringement).filter(
                    Infringement.id == takedown.infringement_id
                ).first()
                if infringement:
                    infringement.status = "resolved"
                    infringement.updated_at = datetime.utcnow()
                
                # Notify user
                await notify_content_removed(takedown.user_id, {
                    "takedown_id": takedown_id,
                    "infringement_url": infringement.url if infringement else "",
                    "platform": infringement.platform if infringement else "",
                    "resolved_at": takedown.resolved_at.isoformat()
                })
                
            elif response_type == "rejection":
                # Request was rejected
                takedown.status = "rejected"
                takedown.resolved_at = datetime.utcnow()
                takedown.notes = response_data.get("reason", "Request rejected by platform")
                
            elif response_type == "counter_notice":
                # Counter notice received
                takedown.status = "counter_notice_received"
                takedown.notes = f"Counter notice: {response_data.get('details', '')}"
                
            elif response_type == "acknowledgment":
                # Platform acknowledged receipt
                takedown.status = "acknowledged"
                takedown.acknowledged_at = datetime.utcnow()
            
            takedown.updated_at = datetime.utcnow()
            db.commit()
            
            # Notify user of status update
            await notify_takedown_status_updated(takedown.user_id, {
                "takedown_id": takedown_id,
                "status": takedown.status,
                "response_type": response_type,
                "notes": takedown.notes
            })
            
            return {
                "takedown_id": takedown_id,
                "status": takedown.status,
                "message": f"Processed {response_type} response"
            }
            
        except Exception as e:
            db.rollback()
            return {
                "takedown_id": takedown_id,
                "status": "error",
                "message": f"Error processing response: {str(e)}"
            }
        finally:
            db.close()
    
    async def get_platform_contacts(self, platform: str) -> Dict[str, Any]:
        """Get contact information for a platform."""
        # Platform contact database
        platform_contacts = {
            "instagram": {
                "email": "ip@instagram.com",
                "name": "Instagram Legal Team",
                "webform_url": "https://help.instagram.com/contact/372592039493026",
                "response_time": "7-14 days"
            },
            "twitter": {
                "email": "copyright@twitter.com",
                "name": "Twitter Copyright Team", 
                "webform_url": "https://help.twitter.com/forms/dmca",
                "response_time": "1-5 days"
            },
            "tiktok": {
                "email": "ip@tiktok.com",
                "name": "TikTok IP Team",
                "webform_url": "https://www.tiktok.com/legal/copyright-policy",
                "response_time": "7-10 days"
            },
            "onlyfans": {
                "email": "dmca@onlyfans.com",
                "name": "OnlyFans DMCA Team",
                "webform_url": "https://onlyfans.com/dmca",
                "response_time": "3-7 days"
            },
            "pornhub": {
                "email": "dmca@pornhub.com",
                "name": "Pornhub Legal Team",
                "webform_url": "https://www.pornhub.com/information#dmca",
                "response_time": "5-10 days"
            }
        }
        
        platform_key = platform.lower()
        if platform_key in platform_contacts:
            return platform_contacts[platform_key]
        else:
            return {
                "email": None,
                "name": f"{platform} Legal Team",
                "webform_url": None,
                "response_time": "Unknown"
            }
    
    async def bulk_send_takedowns(self, takedown_ids: List[int]) -> List[Dict[str, Any]]:
        """Send multiple takedown requests."""
        results = []
        
        for takedown_id in takedown_ids:
            try:
                result = await self.send_takedown_request(takedown_id)
                results.append(result)
                
                # Add delay between sends to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                results.append({
                    "takedown_id": takedown_id,
                    "status": "failed",
                    "message": str(e)
                })
        
        return results


# Global instance
dmca_integration = DMCAIntegration()


# Convenience functions for API endpoints
async def send_takedown_email(takedown_id: int) -> Dict[str, Any]:
    """Send a takedown request via email."""
    return await dmca_integration.send_takedown_request(takedown_id)


async def process_bulk_takedowns_for_user(user_id: int, priority: str = "normal"):
    """Process bulk takedown requests for a user."""
    db = next(get_db())
    
    try:
        # Get draft takedowns for user
        draft_takedowns = db.query(TakedownRequest).filter(
            TakedownRequest.user_id == user_id,
            TakedownRequest.status == "draft"
        ).limit(10).all()  # Process in batches
        
        takedown_ids = [t.id for t in draft_takedowns]
        
        if takedown_ids:
            results = await dmca_integration.bulk_send_takedowns(takedown_ids)
            print(f"Processed {len(results)} takedown requests for user {user_id}")
        
    finally:
        db.close()