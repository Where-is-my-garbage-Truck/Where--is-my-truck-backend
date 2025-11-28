# app/services/location.py
"""
Location Service
================
All location-related calculations:
    - Distance calculation (Haversine formula)
    - ETA estimation
    - Truck status determination
    - Time formatting utilities
"""

import math
from datetime import datetime, timedelta
from typing import Tuple, Optional

from app.config import settings


# ============ DISTANCE CALCULATION ============

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the distance between two points on Earth using Haversine formula.
    
    Args:
        lat1, lng1: First point coordinates (e.g., truck location)
        lat2, lng2: Second point coordinates (e.g., user's home)
    
    Returns:
        Distance in meters
    
    Example:
        >>> haversine_distance(12.9716, 77.5946, 12.9500, 77.6000)
        2487.34  # meters
    """
    R = 6371000  # Earth's radius in meters
    
    # Convert to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    
    # Haversine formula
    a = (math.sin(delta_phi / 2) ** 2 + 
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def format_distance(meters: float) -> str:
    """
    Format distance for display.
    
    Args:
        meters: Distance in meters
    
    Returns:
        Human-readable string like "1.2 km" or "500 m"
    
    Examples:
        >>> format_distance(500)
        "500 m"
        >>> format_distance(1500)
        "1.5 km"
    """
    if meters < 1000:
        return f"{int(meters)} m"
    else:
        km = meters / 1000
        if km < 10:
            return f"{km:.1f} km"
        else:
            return f"{int(km)} km"


# ============ ETA CALCULATION ============

def get_traffic_multiplier() -> float:
    """
    Get traffic multiplier based on current time of day.
    
    Rush hours get higher multiplier (slower travel).
    
    Returns:
        Multiplier value (1.0 = normal, 1.5 = heavy traffic)
    """
    hour = datetime.now().hour
    
    # Morning rush: 7-10 AM
    if 7 <= hour < 10:
        return settings.TRAFFIC_PEAK_MULTIPLIER
    # Evening rush: 5-8 PM
    elif 17 <= hour < 20:
        return settings.TRAFFIC_PEAK_MULTIPLIER
    # Normal hours
    else:
        return settings.TRAFFIC_NORMAL_MULTIPLIER


def estimate_eta(
    distance_meters: float, 
    current_speed: float = 0
) -> Tuple[int, str, str]:
    """
    Estimate time of arrival based on distance and speed.
    
    For garbage trucks:
    - Average speed in residential areas: 10-15 km/h
    - Includes time for stopping at houses
    
    Args:
        distance_meters: Distance in meters
        current_speed: Current truck speed in km/h (0 if unknown)
    
    Returns:
        Tuple of (minutes, text like "~8 mins", arrival time like "06:53 AM")
    
    Example:
        >>> estimate_eta(1500, 15)
        (8, "~8 mins", "06:53 AM")
    """
    # Use current speed if available and reasonable, else use average
    if current_speed > 3:  # Moving
        avg_speed_kmh = min(current_speed * 0.7, 20)  # Factor in stops
    else:
        avg_speed_kmh = settings.AVG_TRUCK_SPEED
    
    # Apply traffic multiplier
    traffic = get_traffic_multiplier()
    effective_speed = avg_speed_kmh / traffic
    
    # Calculate time
    # Speed in m/min = (km/h × 1000) / 60
    speed_m_per_min = (effective_speed * 1000) / 60
    
    if speed_m_per_min > 0:
        minutes = distance_meters / speed_m_per_min
    else:
        minutes = distance_meters / 200  # Fallback: 200m per minute
    
    # Round and ensure minimum 1 minute
    minutes = max(1, int(round(minutes)))
    
    # Format text
    if minutes == 1:
        text = "~1 min"
    elif minutes < 60:
        text = f"~{minutes} mins"
    else:
        hours = minutes // 60
        mins = minutes % 60
        if mins > 0:
            text = f"~{hours}h {mins}m"
        else:
            text = f"~{hours}h"
    
    # Calculate arrival time
    arrival = datetime.now() + timedelta(minutes=minutes)
    arrival_time = arrival.strftime("%I:%M %p")
    
    return minutes, text, arrival_time


# ============ TIME FORMATTING ============

def format_time_ago(dt: Optional[datetime]) -> Optional[int]:
    """
    Calculate seconds since a datetime.
    
    Args:
        dt: Datetime to compare against now
    
    Returns:
        Seconds ago, or None if dt is None
    """
    if dt is None:
        return None
    
    # Ensure we're comparing UTC times
    now = datetime.utcnow()
    diff = now - dt
    return max(0, int(diff.total_seconds()))


def format_time_ago_text(seconds: Optional[int]) -> str:
    """
    Format seconds as human-readable text.
    
    Args:
        seconds: Number of seconds ago
    
    Returns:
        Text like "5 sec ago", "2 min ago", "1 hr ago"
    """
    if seconds is None:
        return "unknown"
    
    if seconds < 60:
        return f"{seconds} sec ago"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} min ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hr ago"
    else:
        days = seconds // 86400
        return f"{days} day ago"


def format_duration(start_time: Optional[datetime]) -> Optional[str]:
    """
    Format duration since start time.
    
    Args:
        start_time: When duty started
    
    Returns:
        Duration string like "2h 15m", or None if no start time
    """
    if start_time is None:
        return None
    
    now = datetime.utcnow()
    diff = now - start_time
    total_minutes = int(diff.total_seconds() / 60)
    
    if total_minutes < 0:
        return "0m"
    
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def format_time(dt: Optional[datetime]) -> Optional[str]:
    """
    Format datetime as time string.
    
    Args:
        dt: Datetime to format
    
    Returns:
        Time string like "06:30 AM", or None if dt is None
    """
    if dt is None:
        return None
    return dt.strftime("%I:%M %p")


# ============ ZONE HELPERS ============

def is_point_in_zone(
    lat: float, lng: float,
    min_lat: float, max_lat: float,
    min_lng: float, max_lng: float
) -> bool:
    """
    Check if a point is inside a zone boundary.
    
    Args:
        lat, lng: Point to check
        min_lat, max_lat, min_lng, max_lng: Zone boundary
    
    Returns:
        True if point is inside zone
    """
    return (min_lat <= lat <= max_lat and 
            min_lng <= lng <= max_lng)


# ============ TRUCK STATUS ============

def determine_truck_status(
    distance_meters: float,
    is_active: bool,
    has_location: bool,
    previous_distance: Optional[float] = None
) -> str:
    """
    Determine truck status relative to user.
    
    Args:
        distance_meters: Current distance from user's home
        is_active: Is truck on duty?
        has_location: Does truck have GPS location?
        previous_distance: Previous distance (to detect direction)
    
    Returns:
        Status string: approaching/arriving/here/passed/offline/not_started
    """
    if not is_active:
        return "offline"
    
    if not has_location:
        return "not_started"
    
    # Check if moving away (passed)
    if previous_distance is not None:
        if distance_meters > previous_distance + 50:  # 50m threshold
            return "passed"
    
    # Distance-based status
    if distance_meters < settings.ALERT_DISTANCE_HERE:  # < 100m
        return "here"
    elif distance_meters < settings.ALERT_DISTANCE_ARRIVING:  # < 500m
        return "arriving"
    else:
        return "approaching"


def should_trigger_alert(
    current_status: str,
    last_alert_type: Optional[str],
    alert_enabled: bool
) -> Tuple[bool, Optional[str]]:
    """
    Determine if an alert should be triggered.
    
    Args:
        current_status: Current truck status
        last_alert_type: Last alert sent to user today
        alert_enabled: Are alerts enabled for user?
    
    Returns:
        Tuple of (should_alert, alert_type)
    """
    if not alert_enabled:
        return False, None
    
    # Map status to alert type
    alert_map = {
        "approaching": "approaching",
        "arriving": "arriving",
        "here": "here"
    }
    
    if current_status not in alert_map:
        return False, None
    
    alert_type = alert_map[current_status]
    
    # Check if this alert already sent
    # Alert priority: approaching < arriving < here
    priority = {"approaching": 1, "arriving": 2, "here": 3}
    
    if last_alert_type and priority.get(alert_type, 0) <= priority.get(last_alert_type, 0):
        return False, None
    
    return True, alert_type


def get_alert_message(alert_type: str, distance_meters: int) -> str:
    """
    Get alert message based on type.
    
    Args:
        alert_type: Type of alert
        distance_meters: Current distance
    
    Returns:
        Alert message string
    """
    messages = {
        "approaching": f"🚛 Garbage truck is {format_distance(distance_meters)} away!",
        "arriving": f"🚛 Truck almost here! Only {format_distance(distance_meters)} away!",
        "here": "🚛 Garbage truck has arrived at your area!"
    }
    return messages.get(alert_type, "🚛 Garbage truck update")