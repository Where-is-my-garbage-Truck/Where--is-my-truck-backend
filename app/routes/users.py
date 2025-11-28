# app/routes/users.py
"""
User Management Routes
======================
User registration, login, and settings.

Endpoints:
    POST   /user/register        - Register new user
    POST   /user/login           - Login with phone
    GET    /user/{id}            - Get user profile
    PUT    /user/{id}/settings   - Update alert settings
    PUT    /user/{id}/home       - Update home location
    POST   /user/{id}/fcm-token  - Update FCM token
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, Zone
from app.schemas import (
    UserRegister, UserResponse, UserLoginRequest, UserLoginResponse,
    UserSettingsUpdate, UserHomeUpdate, FCMTokenUpdate
)
from app.services.location import is_point_in_zone

router = APIRouter(prefix="/user", tags=["User"])


def find_zone_for_location(db: Session, lat: float, lng: float) -> Zone | None:
    """
    Find which zone contains a given location.
    
    Args:
        db: Database session
        lat, lng: Coordinates to check
    
    Returns:
        Zone if found, None otherwise
    """
    zones = db.query(Zone).filter(Zone.is_active == True).all()
    
    for zone in zones:
        if is_point_in_zone(
            lat, lng,
            zone.min_lat, zone.max_lat,
            zone.min_lng, zone.max_lng
        ):
            return zone
    
    return None


@router.post("/register", response_model=UserResponse, status_code=201)
def register_user(
    user: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user.
    
    Automatically assigns zone based on home location.
    """
    # Check if phone already registered
    existing = db.query(User).filter(User.phone == user.phone).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Phone number already registered"
        )
    
    # Find zone for home location
    zone = find_zone_for_location(db, user.home_lat, user.home_lng)
    zone_id = zone.id if zone else None
    zone_name = zone.name if zone else None
    
    # Create user
    db_user = User(
        name=user.name,
        phone=user.phone,
        home_lat=user.home_lat,
        home_lng=user.home_lng,
        home_address=user.home_address,
        zone_id=zone_id
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        id=db_user.id,
        name=db_user.name,
        phone=db_user.phone,
        home_lat=db_user.home_lat,
        home_lng=db_user.home_lng,
        home_address=db_user.home_address,
        zone_id=db_user.zone_id,
        zone_name=zone_name,
        alert_enabled=db_user.alert_enabled,
        alert_distance=db_user.alert_distance,
        alert_type=db_user.alert_type
    )


@router.post("/login", response_model=UserLoginResponse)
def login_user(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    User login with phone number.
    
    Returns user info and assigned zone.
    """
    user = db.query(User).filter(User.phone == request.phone).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="No user registered with this phone number"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account is deactivated"
        )
    
    zone_name = None
    if user.zone_id:
        zone = db.query(Zone).filter(Zone.id == user.zone_id).first()
        zone_name = zone.name if zone else None
    
    return UserLoginResponse(
        user_id=user.id,
        name=user.name,
        phone=user.phone,
        zone_id=user.zone_id,
        zone_name=zone_name,
        home_lat=user.home_lat,
        home_lng=user.home_lng
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get user profile by ID.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    zone_name = None
    if user.zone_id:
        zone = db.query(Zone).filter(Zone.id == user.zone_id).first()
        zone_name = zone.name if zone else None
    
    return UserResponse(
        id=user.id,
        name=user.name,
        phone=user.phone,
        home_lat=user.home_lat,
        home_lng=user.home_lng,
        home_address=user.home_address,
        zone_id=user.zone_id,
        zone_name=zone_name,
        alert_enabled=user.alert_enabled,
        alert_distance=user.alert_distance,
        alert_type=user.alert_type
    )


@router.put("/{user_id}/settings")
def update_settings(
    user_id: int,
    settings: UserSettingsUpdate,
    db: Session = Depends(get_db)
):
    """
    Update user alert settings.
    
    - alert_enabled: Turn alerts on/off
    - alert_distance: Distance threshold for alerts (meters)
    - alert_type: push / missed_call / both / sound
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update only provided fields
    if settings.alert_enabled is not None:
        user.alert_enabled = settings.alert_enabled
    
    if settings.alert_distance is not None:
        user.alert_distance = settings.alert_distance
    
    if settings.alert_type is not None:
        user.alert_type = settings.alert_type.value
    
    db.commit()
    
    return {
        "message": "Settings updated",
        "alert_enabled": user.alert_enabled,
        "alert_distance": user.alert_distance,
        "alert_type": user.alert_type
    }


@router.put("/{user_id}/home")
def update_home_location(
    user_id: int,
    home: UserHomeUpdate,
    db: Session = Depends(get_db)
):
    """
    Update user's home location.
    
    Automatically re-assigns zone based on new location.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update home location
    user.home_lat = home.home_lat
    user.home_lng = home.home_lng
    user.home_address = home.home_address
    
    # Re-assign zone
    zone = find_zone_for_location(db, home.home_lat, home.home_lng)
    old_zone_id = user.zone_id
    user.zone_id = zone.id if zone else None
    zone_name = zone.name if zone else "No service zone found"
    
    # Reset alerts if zone changed
    if old_zone_id != user.zone_id:
        user.last_alert_type = None
        user.last_alert_at = None
    
    db.commit()
    
    return {
        "message": f"Home location updated. You're in: {zone_name}",
        "zone_id": user.zone_id,
        "zone_name": zone_name,
        "zone_changed": old_zone_id != user.zone_id
    }


@router.post("/{user_id}/fcm-token")
def update_fcm_token(
    user_id: int,
    token_data: FCMTokenUpdate,
    db: Session = Depends(get_db)
):
    """
    Update FCM token for push notifications.
    
    Should be called on every app start to keep token fresh.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.fcm_token = token_data.token
    db.commit()
    
    return {"message": "FCM token updated"}

