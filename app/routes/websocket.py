# app/routes/websocket.py
"""
WebSocket Routes
================
Real-time updates for user app.

Instead of polling /track/{user_id} every few seconds,
the user app can connect via WebSocket and receive updates automatically.

Usage:
    Connect to: ws://server/ws/track/{user_id}
    Messages (server → client):
        {
            "type": "location_update" | "status_change" | "error" | "pong",
            "data": { ... },
            "timestamp": "2024-01-15T06:45:30Z"
        }

    Messages (client → server):
        { "type": "ping" }       -> server replies with "pong"
        { "type": "refresh" }    -> server sends current state immediately
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import Dict, Set
import asyncio
import json
import logging
from datetime import datetime

from app.database import SessionLocal
from app.models import User, Truck, Zone
from app.services.location import (
    haversine_distance,
    format_distance,
    estimate_eta,
    format_time_ago,
    determine_truck_status,
)
from app.services.alerts import get_alert_info_for_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


# ============ CONNECTION MANAGER ============


class ConnectionManager:
    """
    Manages WebSocket connections.

    Tracks:
    - Multiple WebSocket connections per user (multi-device / multi-tab)
    - Users per zone (for broadcasting)
    """

    def __init__(self):
        # user_id -> set[WebSocket]
        self.user_connections: Dict[int, Set[WebSocket]] = {}
        # user_id -> zone_id
        self.user_zone: Dict[int, int] = {}
        # zone_id -> set[user_id]
        self.zone_users: Dict[int, Set[int]] = {}

    async def connect(self, websocket: WebSocket, user_id: int, zone_id: int):
        """Accept connection and register user."""
        await websocket.accept()

        self.user_zone[user_id] = zone_id

        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)

        if zone_id not in self.zone_users:
            self.zone_users[zone_id] = set()
        self.zone_users[zone_id].add(user_id)

        logger.info(f"[WS] User {user_id} connected (zone {zone_id})")

    def _remove_connection(self, websocket: WebSocket, user_id: int):
        """Internal helper to remove a connection and clean maps."""
        # Remove websocket from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                # No more connections for this user
                del self.user_connections[user_id]

                # Remove user from zone_users
                zone_id = self.user_zone.pop(user_id, None)
                if zone_id is not None and zone_id in self.zone_users:
                    self.zone_users[zone_id].discard(user_id)
                    if not self.zone_users[zone_id]:
                        del self.zone_users[zone_id]

    def disconnect(self, websocket: WebSocket, user_id: int, zone_id: int | None = None):
        """Public disconnect method called on WebSocket close."""
        self._remove_connection(websocket, user_id)
        logger.info(f"[WS] User {user_id} disconnected")

    async def send_to_user(self, user_id: int, message: dict):
        """Send a message to all active connections of a user."""
        if user_id not in self.user_connections:
            return

        dead_sockets = []

        for ws in list(self.user_connections[user_id]):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"[WS] Error sending to user {user_id}: {e}")
                dead_sockets.append(ws)

        # Clean up dead connections
        for ws in dead_sockets:
            self._remove_connection(ws, user_id)

    async def broadcast_to_zone(self, zone_id: int, message: dict):
        """Broadcast a message to all users connected in a zone."""
        user_ids = list(self.zone_users.get(zone_id, set()))
        for user_id in user_ids:
            await self.send_to_user(user_id, message)

    def get_zone_user_count(self, zone_id: int) -> int:
        """Get number of connected users in a zone."""
        return len(self.zone_users.get(zone_id, set()))


# Global connection manager instance
manager = ConnectionManager()


# ============ WEBSOCKET ENDPOINT ============


@router.websocket("/ws/track/{user_id}")
async def websocket_tracking(websocket: WebSocket, user_id: int):
    """
    WebSocket endpoint for real-time tracking.

    Connect: ws://server/ws/track/{user_id}

    Server will:
        - Validate user and zone
        - Send initial tracking state
        - Respond to:
            - "ping"     -> "pong"
            - "refresh"  -> full state push
    """
    # First DB check: verify user & zone
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=4004, reason="User not found")
            return

        if not user.zone_id:
            await websocket.close(code=4003, reason="No zone assigned to user")
            return

        zone_id = user.zone_id
    finally:
        db.close()

    # Register connection
    await manager.connect(websocket, user_id, zone_id)

    # Send initial state
    await send_current_state(websocket, user_id)

    try:
        # Main receive loop
        while True:
            try:
                raw_data = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"[WS] receive error for user {user_id}: {e}")
                break

            # Parse client message
            try:
                message = json.loads(raw_data)
            except json.JSONDecodeError:
                # Ignore malformed client messages
                continue

            msg_type = message.get("type")

            if msg_type == "ping":
                await websocket.send_json(
                    {
                        "type": "pong",
                        "data": {},
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                )
            elif msg_type == "refresh":
                await send_current_state(websocket, user_id)
            else:
                # Unknown command -> ignore (safe default)
                continue

    finally:
        manager.disconnect(websocket, user_id, zone_id)


# ============ HELPER: BUILD & SEND CURRENT STATE ============


async def send_current_state(websocket: WebSocket, user_id: int):
    """
    Build and send current tracking state to a specific WebSocket.

    This roughly mirrors the /track/{user_id} logic but lighter,
    optimized for WebSocket payloads.
    """
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.send_json(
                {
                    "type": "error",
                    "data": {"message": "User not found"},
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )
            return

        if not user.zone_id:
            await websocket.send_json(
                {
                    "type": "status_change",
                    "data": {
                        "status": "no_zone",
                        "message": "No service zone assigned. Please set your home location.",
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )
            return

        zone = db.query(Zone).filter(Zone.id == user.zone_id).first()
        if not zone:
            await websocket.send_json(
                {
                    "type": "error",
                    "data": {"message": "Zone not found"},
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )
            return

        truck = db.query(Truck).filter(Truck.zone_id == user.zone_id).first()
        if not truck:
            await websocket.send_json(
                {
                    "type": "status_change",
                    "data": {
                        "status": "no_truck",
                        "zone_id": zone.id,
                        "zone_name": zone.name,
                        "message": "No truck assigned to your zone yet.",
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )
            return

        # Base payload
        data = {
            "zone": {
                "id": zone.id,
                "name": zone.name,
                "typical_start": zone.typical_start_time.strftime("%I:%M %p")
                if zone.typical_start_time
                else None,
                "typical_end": zone.typical_end_time.strftime("%I:%M %p")
                if zone.typical_end_time
                else None,
            },
            "truck": {
                "id": truck.id,
                "vehicle_number": truck.vehicle_number,
                "driver_name": truck.driver_name,
                "is_active": truck.is_active,
                "lat": truck.last_lat,
                "lng": truck.last_lng,
                "speed": truck.last_speed,
                "heading": truck.last_heading,
                "last_update": truck.last_update.isoformat() + "Z"
                if truck.last_update
                else None,
                "last_update_seconds_ago": format_time_ago(truck.last_update)
                if truck.last_update
                else None,
            },
            "status": "offline" if not truck.is_active else "active",
        }

        # If truck not active -> send simple status
        if not truck.is_active:
            await websocket.send_json(
                {
                    "type": "status_change",
                    "data": {
                        **data,
                        "message": "Truck is not on duty right now.",
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )
            return

        # If no latest GPS -> waiting state
        if truck.last_lat is None or truck.last_lng is None:
            data["status"] = "not_started"
            data["message"] = "Truck started duty. Waiting for GPS signal..."
            await websocket.send_json(
                {
                    "type": "location_update",
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )
            return

        # If user has no home location -> cannot compute distance/ETA
        if user.home_lat is None or user.home_lng is None:
            data["status"] = "approaching"
            data["message"] = (
                "Please set your home location to see distance and ETA."
            )
            await websocket.send_json(
                {
                    "type": "location_update",
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )
            return

        # Compute distance & ETA
        distance_meters = haversine_distance(
            truck.last_lat, truck.last_lng, user.home_lat, user.home_lng
        )
        minutes, eta_text, arrival = estimate_eta(
            distance_meters, truck.last_speed or 0
        )
        status = determine_truck_status(
            distance_meters=distance_meters,
            is_active=truck.is_active,
            has_location=True,
        )

        data["distance"] = {
            "meters": int(distance_meters),
            "text": format_distance(distance_meters),
        }
        data["eta"] = {
            "minutes": minutes,
            "text": eta_text,
            "arrival_time": arrival,
        }
        data["status"] = status

        # Alert info (for UI & sound)
        alert_info = get_alert_info_for_user(
            db, user, truck, distance_meters
        )
        if alert_info:
            data["alert"] = alert_info

        await websocket.send_json(
            {
                "type": "location_update",
                "data": data,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

    except WebSocketDisconnect:
        # Let outer handler clean up
        raise
    except Exception as e:
        logger.error(f"[WS] send_current_state error for user {user_id}: {e}")
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "data": {"message": "Internal server error"},
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )
        except Exception:
            pass
    finally:
        db.close()


# ============ BROADCAST FUNCTIONS (to call from truck routes) ============


async def broadcast_truck_location(truck_id: int, zone_id: int):
    """
    Broadcast a truck's latest location to all connected users in its zone.

    Intended to be called from the truck location update route:
        background_tasks.add_task(broadcast_truck_location, truck_id, zone_id)
    """
    if manager.get_zone_user_count(zone_id) == 0:
        # No listeners in this zone, skip DB work
        return

    db: Session = SessionLocal()
    try:
        truck = db.query(Truck).filter(Truck.id == truck_id).first()
        if not truck:
            return

        # Get all active users in this zone
        users = db.query(User).filter(
            User.zone_id == zone_id, User.is_active == True
        ).all()

        for user in users:
            # Only send to users who are connected
            if user.id not in manager.user_connections:
                continue

            data = {
                "truck": {
                    "id": truck.id,
                    "vehicle_number": truck.vehicle_number,
                    "is_active": truck.is_active,
                    "lat": truck.last_lat,
                    "lng": truck.last_lng,
                    "speed": truck.last_speed,
                    "heading": truck.last_heading,
                    "last_update": truck.last_update.isoformat() + "Z"
                    if truck.last_update
                    else None,
                }
            }

            if (
                truck.is_active
                and truck.last_lat is not None
                and user.home_lat is not None
            ):
                distance = haversine_distance(
                    truck.last_lat,
                    truck.last_lng,
                    user.home_lat,
                    user.home_lng,
                )
                minutes, eta_text, arrival = estimate_eta(
                    distance, truck.last_speed or 0
                )
                status = determine_truck_status(
                    distance_meters=distance,
                    is_active=truck.is_active,
                    has_location=True,
                )

                data["distance"] = {
                    "meters": int(distance),
                    "text": format_distance(distance),
                }
                data["eta"] = {
                    "minutes": minutes,
                    "text": eta_text,
                    "arrival_time": arrival,
                }
                data["status"] = status

                # Alert info
                alert_info = get_alert_info_for_user(
                    db, user, truck, distance
                )
                if alert_info and alert_info.get("should_alert"):
                    data["alert"] = alert_info

            await manager.send_to_user(
                user.id,
                {
                    "type": "location_update",
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
            )

    except Exception as e:
        logger.error(f"[WS] broadcast_truck_location error: {e}")
    finally:
        db.close()


async def broadcast_truck_status_change(zone_id: int, is_active: bool):
    """
    Broadcast truck duty status change (online/offline) to all users in a zone.

    Intended to be called when driver presses START/STOP duty buttons.
    """
    await manager.broadcast_to_zone(
        zone_id,
        {
            "type": "status_change",
            "data": {
                "status": "active" if is_active else "offline",
                "message": "Garbage Truck started duty"
                if is_active
                else "Truck ended duty",
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )

