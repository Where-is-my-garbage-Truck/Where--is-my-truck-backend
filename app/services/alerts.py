# app/services/alerts.py
"""
Alert Service
=============
Handles all alert-related functionality:
    - Check if alert should be sent
    - Log alerts to prevent duplicates
    - Send push notifications (Firebase)
    - Send missed calls
    - WebSocket notifications
"""

import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models import User, Truck, AlertLog
from app.config import settings
from app.services.location import (
    haversine_distance, 
    determine_truck_status,
    get_alert_message,
    format_distance
)

logger = logging.getLogger(__name__)


# ============ ALERT CHECKING ============

def check_user_alert(
    db: Session,
    user: User,
    truck: Truck
) -> Optional[Dict[str, Any]]:
    """
    Check if a user should receive an alert.
    
    Args:
        db: Database session
        user: User to check
        truck: Truck to check against
    
    Returns:
        Alert info dict if alert should be sent, None otherwise
    """
    # Skip if alerts disabled
    if not user.alert_enabled:
        return None
    
    # Skip if truck not active or no location
    if not truck.is_active or truck.last_lat is None or truck.last_lng is None:
        return None
    
    # Skip if user has no home location
    if user.home_lat is None or user.home_lng is None:
        return None
    
    # Calculate distance
    distance = haversine_distance(
        truck.last_lat, truck.last_lng,
        user.home_lat, user.home_lng
    )
    
    # Determine status
    status = determine_truck_status(
        distance_meters=distance,
        is_active=truck.is_active,
        has_location=True
    )
    
    # Check if this status should trigger alert
    alert_type = None
    if status == "here" and distance < settings.ALERT_DISTANCE_HERE:
        alert_type = "here"
    elif status == "arriving" and distance < settings.ALERT_DISTANCE_ARRIVING:
        alert_type = "arriving"
    elif status == "approaching" and distance < settings.ALERT_DISTANCE_APPROACHING:
        # Only alert if within user's preferred distance
        if distance <= user.alert_distance:
            alert_type = "approaching"
    
    if alert_type is None:
        return None
    
    # Check if already alerted today
    today = date.today()
    existing_alert = db.query(AlertLog).filter(
        AlertLog.user_id == user.id,
        AlertLog.truck_id == truck.id,
        AlertLog.alert_date == today,
        AlertLog.alert_type == alert_type
    ).first()
    
    if existing_alert:
        return None
    
    # Also check if a higher priority alert was already sent
    # Priority: approaching < arriving < here
    priority_map = {"approaching": 1, "arriving": 2, "here": 3}
    current_priority = priority_map.get(alert_type, 0)
    
    higher_alert = db.query(AlertLog).filter(
        AlertLog.user_id == user.id,
        AlertLog.truck_id == truck.id,
        AlertLog.alert_date == today
    ).all()
    
    for alert in higher_alert:
        if priority_map.get(alert.alert_type, 0) >= current_priority:
            return None
    
    # Return alert info
    return {
        "user_id": user.id,
        "truck_id": truck.id,
        "alert_type": alert_type,
        "distance_meters": int(distance),
        "message": get_alert_message(alert_type, int(distance)),
        "should_play_sound": alert_type in ["arriving", "here"],
        "truck_lat": truck.last_lat,
        "truck_lng": truck.last_lng
    }


def check_alerts_for_truck(
    db: Session,
    truck: Truck
) -> List[Dict[str, Any]]:
    """
    Check all users in truck's zone for alerts.
    
    Args:
        db: Database session
        truck: Truck that updated location
    
    Returns:
        List of alert info dicts
    """
    if not truck.zone_id:
        return []
    
    # Get all users in this zone with alerts enabled
    users = db.query(User).filter(
        User.zone_id == truck.zone_id,
        User.alert_enabled == True,
        User.is_active == True
    ).all()
    
    alerts = []
    for user in users:
        alert = check_user_alert(db, user, truck)
        if alert:
            alerts.append(alert)
    
    return alerts


# ============ ALERT LOGGING ============

def log_alert(
    db: Session,
    user_id: int,
    truck_id: int,
    alert_type: str,
    distance_meters: int,
    truck_lat: float,
    truck_lng: float,
    delivery_method: str = "push"
) -> AlertLog:
    """
    Log an alert to prevent duplicate sending.
    
    Args:
        db: Database session
        user_id: User who received alert
        truck_id: Truck that triggered alert
        alert_type: Type of alert (approaching/arriving/here)
        distance_meters: Distance when alert was sent
        truck_lat, truck_lng: Truck location when alert sent
        delivery_method: How alert was delivered (push/missed_call/sound)
    
    Returns:
        Created AlertLog record
    """
    alert_log = AlertLog(
        user_id=user_id,
        truck_id=truck_id,
        alert_date=date.today(),
        alert_type=alert_type,
        distance_meters=distance_meters,
        truck_lat=truck_lat,
        truck_lng=truck_lng,
        delivery_method=delivery_method,
        delivered=True
    )
    
    db.add(alert_log)
    
    # Update user's last alert info
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.last_alert_type = alert_type
        user.last_alert_at = datetime.utcnow()
    
    db.commit()
    
    return alert_log


def reset_user_alerts(db: Session, user_id: int):
    """
    Reset user's alert state (call when truck leaves zone or day changes).
    
    Args:
        db: Database session
        user_id: User to reset
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.last_alert_type = None
        user.last_alert_at = None
        db.commit()


def reset_zone_alerts(db: Session, zone_id: int):
    """
    Reset alert state for all users in a zone.
    
    Args:
        db: Database session
        zone_id: Zone to reset
    """
    db.query(User).filter(User.zone_id == zone_id).update({
        User.last_alert_type: None,
        User.last_alert_at: None
    })
    db.commit()


# ============ NOTIFICATION SENDING ============

async def send_push_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: Optional[Dict] = None
) -> bool:
    """
    Send push notification via Firebase Cloud Messaging.
    
    Args:
        fcm_token: User's FCM token
        title: Notification title
        body: Notification body
        data: Additional data payload
    
    Returns:
        True if sent successfully
    
    Note: Requires FCM_SERVER_KEY in settings.
    """
    if not settings.FCM_SERVER_KEY:
        logger.warning("FCM_SERVER_KEY not configured, skipping push notification")
        return False
    
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://fcm.googleapis.com/fcm/send",
                headers={
                    "Authorization": f"key={settings.FCM_SERVER_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "to": fcm_token,
                    "notification": {
                        "title": title,
                        "body": body,
                        "sound": "default"
                    },
                    "data": data or {},
                    "priority": "high"
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Push notification sent successfully")
                return True
            else:
                logger.error(f"FCM error: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error sending push notification: {e}")
        return False


async def send_missed_call(phone: str) -> bool:
    """
    Send missed call to user.
    
    Args:
        phone: User's phone number
    
    Returns:
        True if call initiated successfully
    
    Note: Requires MISSED_CALL_API_KEY and MISSED_CALL_API_URL in settings.
    """
    if not settings.MISSED_CALL_API_KEY or not settings.MISSED_CALL_API_URL:
        logger.warning("Missed call API not configured, skipping")
        return False
    
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            # This is a generic example - adjust for your actual provider
            # (MSG91, Exotel, Twilio, etc.)
            response = await client.post(
                settings.MISSED_CALL_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.MISSED_CALL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "to": phone,
                    "duration": 5  # Ring for 5 seconds
                }
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Missed call initiated to {phone}")
                return True
            else:
                logger.error(f"Missed call error: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error initiating missed call: {e}")
        return False


async def send_alert(
    db: Session,
    alert_info: Dict[str, Any],
    user: User
) -> bool:
    """
    Send alert to user based on their preferences.
    
    Args:
        db: Database session
        alert_info: Alert information dict
        user: User to send alert to
    
    Returns:
        True if at least one delivery method succeeded
    """
    success = False
    delivery_method = "sound"  # Default
    
    # Prepare notification content
    title = "🚛 Garbage Truck Alert"
    body = alert_info["message"]
    data = {
        "type": "truck_alert",
        "alert_type": alert_info["alert_type"],
        "distance": str(alert_info["distance_meters"]),
        "play_sound": str(alert_info["should_play_sound"]),
        "truck_lat": str(alert_info["truck_lat"]),
        "truck_lng": str(alert_info["truck_lng"])
    }
    
    # Send based on user preference
    if user.alert_type in ["push", "both"]:
        if user.fcm_token:
            push_success = await send_push_notification(
                user.fcm_token, title, body, data
            )
            if push_success:
                success = True
                delivery_method = "push"
    
    if user.alert_type in ["missed_call", "both"]:
        call_success = await send_missed_call(user.phone)
        if call_success:
            success = True
            delivery_method = "missed_call" if delivery_method == "sound" else "both"
    
    # Log the alert
    if success or user.alert_type == "sound":
        log_alert(
            db=db,
            user_id=alert_info["user_id"],
            truck_id=alert_info["truck_id"],
            alert_type=alert_info["alert_type"],
            distance_meters=alert_info["distance_meters"],
            truck_lat=alert_info["truck_lat"],
            truck_lng=alert_info["truck_lng"],
            delivery_method=delivery_method
        )
        return True
    
    return success


# ============ ALERT INFO FOR RESPONSE ============

def get_alert_info_for_user(
    db: Session,
    user: User,
    truck: Truck,
    distance_meters: float
) -> Optional[Dict[str, Any]]:
    """
    Get alert info to include in tracking response.
    
    This doesn't send the alert, just returns info for the app
    to display and play sound if needed.
    
    Args:
        db: Database session
        user: User making request
        truck: Truck being tracked
        distance_meters: Current distance
    
    Returns:
        Alert info dict or None
    """
    if not user.alert_enabled:
        return None
    
    status = determine_truck_status(
        distance_meters=distance_meters,
        is_active=truck.is_active,
        has_location=truck.last_lat is not None
    )
    
    # Determine alert type based on distance
    alert_type = None
    should_alert = False
    
    if status == "here":
        alert_type = "here"
    elif status == "arriving":
        alert_type = "arriving"
    elif status == "approaching" and distance_meters <= user.alert_distance:
        alert_type = "approaching"
    
    if alert_type is None:
        return None
    
    # Check if already alerted
    today = date.today()
    existing = db.query(AlertLog).filter(
        AlertLog.user_id == user.id,
        AlertLog.truck_id == truck.id,
        AlertLog.alert_date == today,
        AlertLog.alert_type == alert_type
    ).first()
    
    should_alert = existing is None
    
    return {
        "should_alert": should_alert,
        "alert_type": alert_type,
        "distance_meters": int(distance_meters),
        "message": get_alert_message(alert_type, int(distance_meters)),
        "play_sound": should_alert and alert_type in ["arriving", "here"]
    }