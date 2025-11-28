# app/schemas.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

# ================== USER SCHEMAS ==================
class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)

class UserResponse(BaseModel):
    id: int
    name: str
    phone: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ================== DRIVER SCHEMAS ==================
class DriverCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    vehicle_number: str = Field(..., min_length=2, max_length=20)

class DriverResponse(BaseModel):
    id: int
    name: str
    phone: str
    vehicle_number: str
    is_online: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ================== LOCATION SCHEMAS ==================
class LocationUpdate(BaseModel):
    """Driver sends this to update location"""
    driver_id: int
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    heading: Optional[float] = Field(default=0, ge=0, le=360)
    speed: Optional[float] = Field(default=0, ge=0)


class LocationResponse(BaseModel):
    """Location returned to users"""
    driver_id: int
    driver_name: str
    vehicle_number: str
    latitude: float
    longitude: float
    heading: float
    speed: float
    timestamp: datetime
    is_online: bool
    
    class Config:
        from_attributes = True


class LocationHistory(BaseModel):
    """Driver's historical route"""
    latitude: float
    longitude: float
    heading: float
    speed: float
    timestamp: datetime
    
    class Config:
        from_attributes = True


# ================== BATCH LOCATION SYNC ==================
class LocationPoint(BaseModel):
    """Single point (same as LocationUpdate but without driver_id)"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    heading: float = Field(default=0, ge=0, le=360)
    speed: float = Field(default=0, ge=0)

class BatchLocationUpdate(BaseModel):
    """When driver syncs multiple offline points"""
    driver_id: int
    locations: List[LocationPoint]
