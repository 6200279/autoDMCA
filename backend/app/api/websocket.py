from typing import Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json
import asyncio
from datetime import datetime

from app.core.security import verify_token
from app.db.session import get_db
from app.db.models.user import User


class ConnectionManager:
    """WebSocket connection manager for real-time updates."""
    
    def __init__(self):
        # Store connections by user_id
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Store connection metadata
        self.connection_info: Dict[WebSocket, Dict] = {}
        
    async def connect(self, websocket: WebSocket, user_id: int, session_info: Dict):
        """Accept and store WebSocket connection."""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        self.active_connections[user_id].append(websocket)
        self.connection_info[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "session_info": session_info
        }
        
        # Send welcome message
        await self.send_personal_message(websocket, {
            "type": "connection_established",
            "message": "Connected to real-time updates",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        if websocket in self.connection_info:
            user_id = self.connection_info[websocket]["user_id"]
            
            # Remove from active connections
            if user_id in self.active_connections:
                if websocket in self.active_connections[user_id]:
                    self.active_connections[user_id].remove(websocket)
                
                # Clean up empty lists
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove connection info
            del self.connection_info[websocket]
    
    async def send_personal_message(self, websocket: WebSocket, message: Dict):
        """Send message to specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception:
            # Connection might be closed
            self.disconnect(websocket)
    
    async def send_to_user(self, user_id: int, message: Dict):
        """Send message to all connections for a specific user."""
        if user_id in self.active_connections:
            # Create list copy to avoid modification during iteration
            connections = self.active_connections[user_id].copy()
            
            for websocket in connections:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception:
                    # Remove failed connection
                    self.disconnect(websocket)
    
    async def broadcast_to_all(self, message: Dict):
        """Broadcast message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)
    
    async def send_personal_message_by_user_id(self, user_id: int, message: Dict):
        """Send message to all connections for a specific user (alias for send_to_user)."""
        await self.send_to_user(user_id, message)
    
    def get_user_connections_count(self, user_id: int) -> int:
        """Get number of active connections for a user."""
        return len(self.active_connections.get(user_id, []))
    
    def get_total_connections(self) -> int:
        """Get total number of active connections."""
        return sum(len(connections) for connections in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()


async def get_websocket_user(websocket: WebSocket, token: str, db: Session) -> User:
    """Authenticate user from WebSocket token."""
    try:
        payload = verify_token(token)
        if payload is None or payload.get("type") != "access":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()
        
        if not user or not user.is_active:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found or inactive")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
        
        return user
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")


async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    """WebSocket endpoint for real-time updates."""
    user = await get_websocket_user(websocket, token, db)
    
    # Session info
    session_info = {
        "user_agent": websocket.headers.get("user-agent"),
        "ip_address": websocket.client.host if websocket.client else None,
    }
    
    await manager.connect(websocket, user.id, session_info)
    
    try:
        while True:
            # Listen for messages from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_client_message(websocket, user, message)
            except json.JSONDecodeError:
                await manager.send_personal_message(websocket, {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                await manager.send_personal_message(websocket, {
                    "type": "error",
                    "message": f"Error processing message: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)


async def handle_client_message(websocket: WebSocket, user: User, message: Dict):
    """Handle messages from WebSocket client."""
    message_type = message.get("type")
    
    if message_type == "ping":
        # Respond to ping with pong
        await manager.send_personal_message(websocket, {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif message_type == "subscribe":
        # Subscribe to specific event types
        event_types = message.get("events", [])
        await manager.send_personal_message(websocket, {
            "type": "subscription_confirmed",
            "events": event_types,
            "message": f"Subscribed to {len(event_types)} event types",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif message_type == "get_stats":
        # Send current connection stats
        await manager.send_personal_message(websocket, {
            "type": "connection_stats",
            "user_connections": manager.get_user_connections_count(user.id),
            "total_connections": manager.get_total_connections(),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    else:
        await manager.send_personal_message(websocket, {
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": datetime.utcnow().isoformat()
        })


# Event notification functions
async def notify_infringement_found(user_id: int, infringement_data: Dict):
    """Notify user of new infringement."""
    await manager.send_to_user(user_id, {
        "type": "infringement_found",
        "data": infringement_data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_takedown_status_updated(user_id: int, takedown_data: Dict):
    """Notify user of takedown status update."""
    await manager.send_to_user(user_id, {
        "type": "takedown_status_updated",
        "data": takedown_data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_scan_completed(user_id: int, scan_data: Dict):
    """Notify user that scan has completed."""
    await manager.send_to_user(user_id, {
        "type": "scan_completed",
        "data": scan_data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_content_removed(user_id: int, removal_data: Dict):
    """Notify user of successful content removal."""
    await manager.send_to_user(user_id, {
        "type": "content_removed",
        "data": removal_data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_alert(user_id: int, alert_data: Dict):
    """Send alert notification to user."""
    await manager.send_to_user(user_id, {
        "type": "alert",
        "data": alert_data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_system_maintenance(message: str, scheduled_time: Optional[datetime] = None):
    """Broadcast system maintenance notification."""
    await manager.broadcast_to_all({
        "type": "system_maintenance",
        "message": message,
        "scheduled_time": scheduled_time.isoformat() if scheduled_time else None,
        "timestamp": datetime.utcnow().isoformat()
    })


# WebSocket health check
async def websocket_health_check():
    """Periodic health check for WebSocket connections."""
    while True:
        try:
            # Send ping to all connections
            ping_message = {
                "type": "health_check",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Clean up stale connections
            total_before = manager.get_total_connections()
            await manager.broadcast_to_all(ping_message)
            total_after = manager.get_total_connections()
            
            if total_before != total_after:
                print(f"Cleaned up {total_before - total_after} stale WebSocket connections")
            
        except Exception as e:
            print(f"WebSocket health check error: {e}")
        
        # Wait 30 seconds before next health check
        await asyncio.sleep(30)


# Start health check task
asyncio.create_task(websocket_health_check())


# Notification functions for scanning system
async def notify_scan_progress(user_id: int, profile_id: int, progress: float, message: str):
    """Notify about scan progress."""
    await manager.send_personal_message_by_user_id(
        user_id,
        {
            "type": "scan_progress",
            "profile_id": profile_id,
            "progress": progress,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def notify_infringement_found(user_id: int, infringement_data: dict):
    """Notify about found infringement."""
    await manager.send_personal_message_by_user_id(
        user_id,
        {
            "type": "infringement_found",
            "data": infringement_data,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def notify_scan_completed(user_id: int, profile_id: int, results: dict):
    """Notify about scan completion."""
    await manager.send_personal_message_by_user_id(
        user_id,
        {
            "type": "scan_completed",
            "profile_id": profile_id,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    )