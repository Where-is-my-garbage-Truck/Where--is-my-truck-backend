# app/routes/zones.py
"""
Zone Management Routes (Admin)
==============================
CRUD operations for service zones/wards.

Endpoints:
    POST   /zones/           - Create zone
    GET    /zones/           - List zones
    GET    /zones/{id}       - Get zone details
    PUT    /zones/{id}       - Update zone
    DELETE /zones/{id}       - Deactivate zone
    GET    /zones/{id}/stats - Zone statistics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import Zone, Truck, User
from app.schemas import (
    ZoneCreate, ZoneUpdate, ZoneResponse, ZoneWithTruck
)

router = APIRouter(prefix="/zones", tags=["Zones (Admin)"])


@router.post("/", response_model=ZoneResponse, status_code=201)
def create_zone(
    zone: ZoneCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new zone/ward.
    
    Zone is defined by a rectangular boundary (min/max lat/lng).
    """
    # Check if zone name already exists
    existing = db.query(Zone).filter(Zone.name == zone.name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Zone '{zone.name}' already exists"
        )
    
    db_zone = Zone(
        name=zone.name,
        city=zone.city,
        min_lat=zone.min_lat,
        max_lat=zone.max_lat,
        min_lng=zone.min_lng,
        max_lng=zone.max_lng,
        typical_start_time=zone.typical_start_time,
        typical_end_time=zone.typical_end_time
    )
    
    db.add(db_zone)
    db.commit()
    db.refresh(db_zone)
    
    return db_zone


@router.get("/", response_model=List[ZoneWithTruck])
def list_zones(
    active_only: bool = Query(True, description="Only show active zones"),
    city: Optional[str] = Query(None, description="Filter by city"),
    db: Session = Depends(get_db)
):
    """
    List all zones with their truck information.
    """
    query = db.query(Zone)
    
    if active_only:
        query = query.filter(Zone.is_active == True)
    
    if city:
        query = query.filter(Zone.city == city)
    
    zones = query.order_by(Zone.name).all()
    
    # Build response with truck info
    result = []
    for zone in zones:
        zone_data = ZoneWithTruck(
            id=zone.id,
            name=zone.name,
            city=zone.city,
            min_lat=zone.min_lat,
            max_lat=zone.max_lat,
            min_lng=zone.min_lng,
            max_lng=zone.max_lng,
            typical_start_time=zone.typical_start_time,
            typical_end_time=zone.typical_end_time,
            is_active=zone.is_active,
            truck_id=zone.truck.id if zone.truck else None,
            truck_vehicle_number=zone.truck.vehicle_number if zone.truck else None,
            truck_is_active=zone.truck.is_active if zone.truck else None
        )
        result.append(zone_data)
    
    return result


@router.get("/{zone_id}", response_model=ZoneWithTruck)
def get_zone(
    zone_id: int,
    db: Session = Depends(get_db)
):
    """
    Get zone details by ID.
    """
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    return ZoneWithTruck(
        id=zone.id,
        name=zone.name,
        city=zone.city,
        min_lat=zone.min_lat,
        max_lat=zone.max_lat,
        min_lng=zone.min_lng,
        max_lng=zone.max_lng,
        typical_start_time=zone.typical_start_time,
        typical_end_time=zone.typical_end_time,
        is_active=zone.is_active,
        truck_id=zone.truck.id if zone.truck else None,
        truck_vehicle_number=zone.truck.vehicle_number if zone.truck else None,
        truck_is_active=zone.truck.is_active if zone.truck else None
    )


@router.put("/{zone_id}", response_model=ZoneResponse)
def update_zone(
    zone_id: int,
    zone_data: ZoneUpdate,
    db: Session = Depends(get_db)
):
    """
    Update zone details.
    """
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Update only provided fields
    update_data = zone_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(zone, field, value)
    
    db.commit()
    db.refresh(zone)
    
    return zone


@router.delete("/{zone_id}")
def delete_zone(
    zone_id: int,
    db: Session = Depends(get_db)
):
    """
    Deactivate a zone (soft delete).
    
    Does not actually delete - just marks as inactive.
    """
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    zone.is_active = False
    db.commit()
    
    return {
        "message": f"Zone '{zone.name}' deactivated",
        "zone_id": zone.id
    }


@router.get("/{zone_id}/stats")
def get_zone_stats(
    zone_id: int,
    db: Session = Depends(get_db)
):
    """
    Get zone statistics.
    
    Returns:
        - User count in zone
        - Truck info and status
        - Today's activity summary
    """
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Count users
    user_count = db.query(User).filter(
        User.zone_id == zone_id,
        User.is_active == True
    ).count()
    
    # Get truck info
    truck = db.query(Truck).filter(Truck.zone_id == zone_id).first()
    truck_info = None
    
    if truck:
        # Count today's locations
        from datetime import date, datetime
        today_start = datetime.combine(date.today(), datetime.min.time())
        
        from app.models import TruckLocation
        location_count = db.query(TruckLocation).filter(
            TruckLocation.truck_id == truck.id,
            TruckLocation.captured_at >= today_start
        ).count()
        
        truck_info = {
            "id": truck.id,
            "vehicle_number": truck.vehicle_number,
            "driver_name": truck.driver_name,
            "is_active": truck.is_active,
            "duty_started_at": truck.duty_started_at,
            "locations_today": location_count
        }
    
    return {
        "zone_id": zone.id,
        "zone_name": zone.name,
        "is_active": zone.is_active,
        "user_count": user_count,
        "truck": truck_info
    }