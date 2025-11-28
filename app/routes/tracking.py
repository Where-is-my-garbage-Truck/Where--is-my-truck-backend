# app/routes/tracking.py
"""
Tracking Routes (User App)
==========================
Main tracking endpoints for the user app.

IMPORTANT: Static routes must come BEFORE dynamic routes!
    - /track/nearby        (static - must be first)
    - /track/zone/{id}     (static prefix)
    - /track/{user_id}     (dynamic - must be last)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import User, Zone, Truck, TruckLocation
from app.schemas import (
    TrackingResponse, TruckInfo, DistanceInfo, ETAInfo, ZoneInfo,
    DutyInfo, AlertInfo, TruckStatus, RouteResponse, RoutePoint
)
from app.services.location import (
    haversine_distance, format_distance, estimate_eta,
    format_time_ago, format_time, format_duration,
    determine_truck_status
)
from app.services.alerts import get_alert_info_for_user

router = APIRouter(prefix="/track", tags=["Tracking"])


# ============================================================
# STATIC ROUTES (Must come BEFORE dynamic routes!)
# ============================================================

@router.get("/nearby")
def find_nearby_trucks(
    lat: float = Query(..., ge=-90, le=90, description="Your latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Your longitude"),
    radius_km: float = Query(5, ge=0.5, le=20, description="Search radius in km"),
    db: Session = Depends(get_db)
):
    """
    Find active trucks near a location.
    
    Useful for:
    - Finding which zone covers a location
    - Discovery before registration
    """
    # Get all active trucks with location
    trucks = db.query(Truck).filter(
        Truck.is_active == True,
        Truck.last_lat.isnot(None),
        Truck.last_lng.isnot(None)
    ).all()
    
    nearby = []
    
    for truck in trucks:
        distance_meters = haversine_distance(
            lat, lng,
            truck.last_lat, truck.last_lng
        )
        distance_km = distance_meters / 1000
        
        if distance_km <= radius_km:
            zone = db.query(Zone).filter(Zone.id == truck.zone_id).first()
            
            nearby.append({
                "truck_id": truck.id,
                "vehicle_number": truck.vehicle_number,
                "zone_id": truck.zone_id,
                "zone_name": zone.name if zone else None,
                "distance_km": round(distance_km, 2),
                "distance_text": format_distance(distance_meters),
                "lat": truck.last_lat,
                "lng": truck.last_lng,
                "last_update_seconds_ago": format_time_ago(truck.last_update)
            })
    
    # Sort by distance
    nearby.sort(key=lambda x: x["distance_km"])
    
    return {
        "search_location": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
        "found": len(nearby),
        "trucks": nearby
    }


@router.get("/zone/{zone_id}")
def get_zone_truck_status(
    zone_id: int,
    db: Session = Depends(get_db)
):
    """
    Get truck status for a zone.
    
    Public endpoint - can be called without user login.
    """
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    truck = db.query(Truck).filter(Truck.zone_id == zone_id).first()
    
    if not truck:
        return {
            "zone_id": zone.id,
            "zone_name": zone.name,
            "has_truck": False,
            "truck": None
        }
    
    return {
        "zone_id": zone.id,
        "zone_name": zone.name,
        "has_truck": True,
        "truck": {
            "id": truck.id,
            "vehicle_number": truck.vehicle_number,
            "is_active": truck.is_active,
            "lat": truck.last_lat,
            "lng": truck.last_lng,
            "speed": truck.last_speed,
            "last_update": truck.last_update,
            "last_update_seconds_ago": format_time_ago(truck.last_update)
        }
    }


# ============================================================
# DYNAMIC ROUTES (Must come AFTER static routes!)
# ============================================================

@router.get("/{user_id}", response_model=TrackingResponse)
def track_truck(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    🌟 MAIN TRACKING ENDPOINT
    
    Returns everything needed for user app tracking screen:
    - Truck location and status
    - Distance from user's home
    - ETA estimate
    - Alert info (should play sound?)
    
    Poll this every 3-5 seconds for live tracking.
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    
    # Check user has zone
    if not user.zone_id:
        raise HTTPException(
            status_code=400,
            detail="Your location is not in any service zone. Please update your home location."
        )
    
    # Get zone
    zone = db.query(Zone).filter(Zone.id == user.zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Build zone info
    zone_info = ZoneInfo(
        id=zone.id,
        name=zone.name,
        typical_start=zone.typical_start_time.strftime("%I:%M %p") if zone.typical_start_time else None,
        typical_end=zone.typical_end_time.strftime("%I:%M %p") if zone.typical_end_time else None
    )
    
    # Get truck for zone
    truck = db.query(Truck).filter(Truck.zone_id == user.zone_id).first()
    
    # No truck assigned
    if not truck:
        return TrackingResponse(
            truck=None,
            distance=None,
            eta=None,
            status=TruckStatus.NO_TRUCK,
            zone=zone_info,
            duty=None,
            alert=None,
            message="No truck assigned to your zone yet."
        )
    
    # Build truck info
    seconds_ago = format_time_ago(truck.last_update) if truck.last_update else None
    
    truck_info = TruckInfo(
        id=truck.id,
        vehicle_number=truck.vehicle_number,
        driver_name=truck.driver_name,
        is_active=truck.is_active,
        lat=truck.last_lat,
        lng=truck.last_lng,
        speed=truck.last_speed,
        heading=truck.last_heading,
        last_update=truck.last_update,
        last_update_seconds_ago=seconds_ago
    )
    
    # Build duty info
    duty_info = None
    if truck.is_active and truck.duty_started_at:
        duty_info = DutyInfo(
            started_at=format_time(truck.duty_started_at),
            duration=format_duration(truck.duty_started_at)
        )
    
    # Truck offline
    if not truck.is_active:
        message = "Truck is not on duty."
        if zone.typical_start_time:
            message += f" Usual timing: {zone.typical_start_time.strftime('%I:%M %p')}"
            if zone.typical_end_time:
                message += f" - {zone.typical_end_time.strftime('%I:%M %p')}"
        
        return TrackingResponse(
            truck=truck_info,
            distance=None,
            eta=None,
            status=TruckStatus.OFFLINE,
            zone=zone_info,
            duty=None,
            alert=None,
            message=message
        )
    
    # Truck active but no location yet
    if truck.last_lat is None or truck.last_lng is None:
        return TrackingResponse(
            truck=truck_info,
            distance=None,
            eta=None,
            status=TruckStatus.NOT_STARTED,
            zone=zone_info,
            duty=duty_info,
            alert=None,
            message="Truck just started. Waiting for GPS signal..."
        )
    
    # User has no home location
    if user.home_lat is None or user.home_lng is None:
        return TrackingResponse(
            truck=truck_info,
            distance=None,
            eta=None,
            status=TruckStatus.APPROACHING,
            zone=zone_info,
            duty=duty_info,
            alert=None,
            message="Please set your home location to see distance and ETA."
        )
    
    # Calculate distance
    distance_meters = haversine_distance(
        truck.last_lat, truck.last_lng,
        user.home_lat, user.home_lng
    )
    
    distance_info = DistanceInfo(
        meters=int(distance_meters),
        text=format_distance(distance_meters)
    )
    
    # Calculate ETA
    minutes, text, arrival = estimate_eta(distance_meters, truck.last_speed)
    eta_info = ETAInfo(
        minutes=minutes,
        text=text,
        arrival_time=arrival
    )
    
    # Determine status
    status = determine_truck_status(
        distance_meters=distance_meters,
        is_active=truck.is_active,
        has_location=True
    )
    
    # Get alert info
    alert_info_dict = get_alert_info_for_user(db, user, truck, distance_meters)
    alert_info = None
    if alert_info_dict:
        alert_info = AlertInfo(
            should_alert=alert_info_dict["should_alert"],
            alert_type=alert_info_dict["alert_type"],
            distance_meters=alert_info_dict["distance_meters"],
            message=alert_info_dict["message"]
        )
    
    return TrackingResponse(
        truck=truck_info,
        distance=distance_info,
        eta=eta_info,
        status=TruckStatus(status),
        zone=zone_info,
        duty=duty_info,
        alert=alert_info,
        message=None
    )


@router.get("/{user_id}/route", response_model=RouteResponse)
def get_truck_route(
    user_id: int,
    minutes: int = Query(60, ge=5, le=480, description="Minutes of history"),
    db: Session = Depends(get_db)
):
    """
    Get truck's route history.
    
    Returns list of GPS points for drawing route on map.
    Default: last 60 minutes.
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.zone_id:
        raise HTTPException(status_code=400, detail="No zone assigned")
    
    # Get truck
    truck = db.query(Truck).filter(Truck.zone_id == user.zone_id).first()
    if not truck:
        return RouteResponse(route=[], total_points=0, from_time=None, to_time=None)
    
    # Get locations
    time_threshold = datetime.utcnow() - timedelta(minutes=minutes)
    
    locations = db.query(TruckLocation).filter(
        TruckLocation.truck_id == truck.id,
        TruckLocation.captured_at >= time_threshold
    ).order_by(TruckLocation.captured_at).all()
    
    # Convert to route points
    route = [
        RoutePoint(
            lat=loc.latitude,
            lng=loc.longitude,
            speed=loc.speed,
            time=loc.captured_at.strftime("%H:%M:%S")
        )
        for loc in locations
    ]
    
    from_time = locations[0].captured_at.strftime("%H:%M") if locations else None
    to_time = locations[-1].captured_at.strftime("%H:%M") if locations else None
    
    return RouteResponse(
        route=route,
        total_points=len(route),
        from_time=from_time,
        to_time=to_time
    )