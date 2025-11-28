# app/schemas.py
"""
Pydantic Schemas
================
Request and response validation models.

Organized by feature:
    - Zone schemas
    - Truck schemas
    - User schemas
    - Location schemas
    - Tracking schemas
    - WebSocket schemas
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime, time, date
from typing import Optional, List, Any
from enum import Enum


# ============ ENUMS ============

class AlertType(str, Enum):
    """Alert notification types"""
    PUSH = "push"
    MISSED_CALL = "missed_call"
    BOTH = "both"
    SOUND = "sound"  # In-app sound only


class TruckStatus(str, Enum):
    """Truck status relative to user"""
    APPROACHING = "approaching"  # > 500m, coming closer
    ARRIVING = "arriving"        # 100-500m
    HERE = "here"                # < 100m
    PASSED = "passed"            # Moving away
    OFFLINE = "offline"          # Truck not on duty
    NOT_STARTED = "not_started"  # On duty but no GPS yet
    NO_TRUCK = "no_truck"        # No truck assigned to zone


# ============ ZONE SCHEMAS ============

class ZoneCreate(BaseModel):
    """Create a new zone"""
    name: str = Field(..., min_length=2, max_length=100, 
                      description="Zone name like 'Ward 5'")
    city: str = Field(default="", max_length=100)
    min_lat: float = Field(..., ge=-90, le=90, description="Southwest latitude")
    max_lat: float = Field(..., ge=-90, le=90, description="Northeast latitude")
    min_lng: float = Field(..., ge=-180, le=180, description="Southwest longitude")
    max_lng: float = Field(..., ge=-180, le=180, description="Northeast longitude")
    typical_start_time: Optional[time] = Field(None, description="Usual start time")
    typical_end_time: Optional[time] = Field(None, description="Usual end time")
    
    @field_validator('max_lat')
    @classmethod
    def validate_lat_range(cls, v, info):
        if 'min_lat' in info.data and v <= info.data['min_lat']:
            raise ValueError('max_lat must be greater than min_lat')
        return v
    
    @field_validator('max_lng')
    @classmethod
    def validate_lng_range(cls, v, info):
        if 'min_lng' in info.data and v <= info.data['min_lng']:
            raise ValueError('max_lng must be greater than min_lng')
        return v


class ZoneUpdate(BaseModel):
    """Update zone details"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    min_lat: Optional[float] = Field(None, ge=-90, le=90)
    max_lat: Optional[float] = Field(None, ge=-90, le=90)
    min_lng: Optional[float] = Field(None, ge=-180, le=180)
    max_lng: Optional[float] = Field(None, ge=-180, le=180)
    typical_start_time: Optional[time] = None
    typical_end_time: Optional[time] = None
    is_active: Optional[bool] = None


class ZoneResponse(BaseModel):
    """Zone response"""
    id: int
    name: str
    city: str
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float
    typical_start_time: Optional[time]
    typical_end_time: Optional[time]
    is_active: bool
    
    class Config:
        from_attributes = True


class ZoneWithTruck(ZoneResponse):
    """Zone with truck info"""
    truck_id: Optional[int] = None
    truck_vehicle_number: Optional[str] = None
    truck_is_active: Optional[bool] = None


# ============ TRUCK SCHEMAS ============

class TruckCreate(BaseModel):
    """Create a new truck"""
    vehicle_number: str = Field(..., min_length=2, max_length=20,
                                description="Vehicle registration number")
    name: Optional[str] = Field(None, max_length=100, 
                                description="Friendly name like 'Truck 1'")
    driver_name: Optional[str] = Field(None, max_length=100)
    driver_phone: str = Field(..., min_length=10, max_length=20,
                              description="Driver's phone for login")
    zone_id: Optional[int] = Field(None, description="Assigned zone ID")


class TruckUpdate(BaseModel):
    """Update truck details"""
    name: Optional[str] = Field(None, max_length=100)
    driver_name: Optional[str] = Field(None, max_length=100)
    driver_phone: Optional[str] = Field(None, min_length=10, max_length=20)
    zone_id: Optional[int] = None


class TruckResponse(BaseModel):
    """Truck response"""
    id: int
    vehicle_number: str
    name: Optional[str]
    driver_name: Optional[str]
    driver_phone: str
    zone_id: Optional[int]
    is_active: bool
    duty_started_at: Optional[datetime]
    last_lat: Optional[float]
    last_lng: Optional[float]
    last_speed: Optional[float]
    last_heading: Optional[float]
    last_update: Optional[datetime]
    
    class Config:
        from_attributes = True


class DriverLoginRequest(BaseModel):
    """Driver login with phone"""
    phone: str = Field(..., min_length=10, max_length=20)


class DriverLoginResponse(BaseModel):
    """Driver login response"""
    truck_id: int
    vehicle_number: str
    driver_name: Optional[str]
    zone_id: Optional[int]
    zone_name: Optional[str]
    is_active: bool


class DutyResponse(BaseModel):
    """Start/Stop duty response"""
    status: str  # "active" or "inactive"
    message: str
    started_at: Optional[datetime] = None
    duration: Optional[str] = None


# ============ LOCATION SCHEMAS ============

class LocationUpdate(BaseModel):
    """Single location update from driver app"""
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    speed: float = Field(default=0, ge=0, description="Speed in km/h")
    heading: float = Field(default=0, ge=0, le=360, description="Direction 0-360")
    accuracy: Optional[float] = Field(None, ge=0, description="GPS accuracy in meters")
    captured_at: datetime = Field(..., description="When GPS was captured on device")


class LocationBatchSync(BaseModel):
    """Batch sync of offline locations"""
    locations: List[LocationUpdate] = Field(..., min_length=1, max_length=1000)


class LocationSyncResponse(BaseModel):
    """Response for batch sync"""
    synced: int
    failed: int
    message: str


class RoutePoint(BaseModel):
    """Single point in a route"""
    lat: float
    lng: float
    speed: float
    time: str  # "06:30:15"
    
    class Config:
        from_attributes = True


# ============ USER SCHEMAS ============

class UserRegister(BaseModel):
    """User registration"""
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    home_lat: float = Field(..., ge=-90, le=90)
    home_lng: float = Field(..., ge=-180, le=180)
    home_address: Optional[str] = Field(None, max_length=500)


class UserLoginRequest(BaseModel):
    """User login"""
    phone: str = Field(..., min_length=10, max_length=20)


class UserResponse(BaseModel):
    """User response"""
    id: int
    name: str
    phone: str
    home_lat: Optional[float]
    home_lng: Optional[float]
    home_address: Optional[str]
    zone_id: Optional[int]
    zone_name: Optional[str] = None
    alert_enabled: bool
    alert_distance: int
    alert_type: str
    
    class Config:
        from_attributes = True


class UserLoginResponse(BaseModel):
    """User login response"""
    user_id: int
    name: str
    phone: str
    zone_id: Optional[int]
    zone_name: Optional[str]
    home_lat: Optional[float]
    home_lng: Optional[float]


class UserSettingsUpdate(BaseModel):
    """Update user settings"""
    alert_enabled: Optional[bool] = None
    alert_distance: Optional[int] = Field(None, ge=50, le=5000)
    alert_type: Optional[AlertType] = None


class UserHomeUpdate(BaseModel):
    """Update user's home location"""
    home_lat: float = Field(..., ge=-90, le=90)
    home_lng: float = Field(..., ge=-180, le=180)
    home_address: Optional[str] = Field(None, max_length=500)


class FCMTokenUpdate(BaseModel):
    """Update FCM token for push notifications"""
    token: str


# ============ TRACKING SCHEMAS (Main Feature!) ============

class TruckInfo(BaseModel):
    """Truck information for tracking"""
    id: int
    vehicle_number: str
    driver_name: Optional[str]
    is_active: bool
    lat: Optional[float]
    lng: Optional[float]
    speed: Optional[float]
    heading: Optional[float]
    last_update: Optional[datetime]
    last_update_seconds_ago: Optional[int]


class DistanceInfo(BaseModel):
    """Distance information"""
    meters: int
    text: str  # "1.2 km" or "500 m"


class ETAInfo(BaseModel):
    """ETA information"""
    minutes: int
    text: str  # "~8 mins"
    arrival_time: str  # "06:53 AM"


class ZoneInfo(BaseModel):
    """Zone information for tracking"""
    id: int
    name: str
    typical_start: Optional[str]
    typical_end: Optional[str]


class DutyInfo(BaseModel):
    """Duty information"""
    started_at: Optional[str]  # "06:30 AM"
    duration: Optional[str]    # "2h 15m"


class AlertInfo(BaseModel):
    """Alert state for user"""
    should_alert: bool
    alert_type: Optional[str]  # approaching/arriving/here
    distance_meters: Optional[int]
    message: Optional[str]


class TrackingResponse(BaseModel):
    """
    Main tracking response for user app.
    Contains everything needed to display tracking UI.
    """
    truck: Optional[TruckInfo]
    distance: Optional[DistanceInfo]
    eta: Optional[ETAInfo]
    status: TruckStatus
    zone: ZoneInfo
    duty: Optional[DutyInfo]
    alert: Optional[AlertInfo]
    message: Optional[str] = None


class RouteResponse(BaseModel):
    """Route history response"""
    route: List[RoutePoint]
    total_points: int
    from_time: Optional[str]
    to_time: Optional[str]


# ============ WEBSOCKET SCHEMAS ============

class WSMessage(BaseModel):
    """WebSocket message format"""
    type: str  # "location_update", "alert", "status_change"
    data: Any
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSLocationUpdate(BaseModel):
    """WebSocket location update"""
    truck_id: int
    lat: float
    lng: float
    speed: float
    heading: float
    timestamp: datetime


class WSAlert(BaseModel):
    """WebSocket alert message"""
    alert_type: str  # approaching/arriving/here
    message: str
    distance_meters: int
    play_sound: bool