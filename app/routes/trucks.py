# app/routes/trucks.py
"""
Truck Management & Driver App Routes
=====================================
Endpoints for:
    - Admin: Manage trucks
    - Driver App: Login, Start/Stop duty, Send location

Endpoints:
    POST   /truck/               - Create truck (Admin)
    GET    /truck/all            - List trucks (Admin)
    PUT    /truck/{id}           - Update truck (Admin)
    POST   /truck/{id}/assign-zone - Assign zone (Admin)
    
    POST   /truck/login          - Driver login
    POST   /truck/{id}/start     - Start duty
    POST   /truck/{id}/stop      - Stop duty
    POST   /truck/{id}/location  - Send GPS location
    POST   /truck/{id}/sync      - Sync offline locations
    GET    /truck/{id}/status    - Get truck status
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, date

from app.database import get_db
from app.models import Zone, Truck, TruckLocation, User
from app.schemas import (
    TruckCreate, TruckUpdate, TruckResponse,
    DriverLoginRequest, DriverLoginResponse, DutyResponse,
    LocationUpdate, LocationBatchSync, LocationSyncResponse
)
from app.services.location import format_duration
from app.services.alerts import check_alerts_for_truck, send_alert, reset_zone_alerts

router = APIRouter(prefix="/truck", tags=["Truck / Driver"])


# ============ ADMIN ENDPOINTS ============

@router.post("/", response_model=TruckResponse, status_code=201)
def create_truck(
    truck: TruckCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new truck. (Admin)
    """
    # Check vehicle number uniqueness
    existing = db.query(Truck).filter(
        Truck.vehicle_number == truck.vehicle_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Vehicle number '{truck.vehicle_number}' already exists"
        )
    
    # Check phone uniqueness
    existing_phone = db.query(Truck).filter(
        Truck.driver_phone == truck.driver_phone
    ).first()
    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Driver phone number already registered"
        )
    
    # Check zone exists and not already assigned
    if truck.zone_id:
        zone = db.query(Zone).filter(Zone.id == truck.zone_id).first()
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")
        
        existing_truck = db.query(Truck).filter(
            Truck.zone_id == truck.zone_id
        ).first()
        if existing_truck:
            raise HTTPException(
                status_code=400,
                detail=f"Zone already has truck: {existing_truck.vehicle_number}"
            )
    
    db_truck = Truck(
        vehicle_number=truck.vehicle_number,
        name=truck.name,
        driver_name=truck.driver_name,
        driver_phone=truck.driver_phone,
        zone_id=truck.zone_id
    )
    
    db.add(db_truck)
    db.commit()
    db.refresh(db_truck)
    
    return db_truck


@router.get("/all", response_model=List[TruckResponse])
def list_trucks(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    List all trucks. (Admin)
    """
    query = db.query(Truck)
    
    if active_only:
        query = query.filter(Truck.is_active == True)
    
    return query.order_by(Truck.id).all()


@router.put("/{truck_id}", response_model=TruckResponse)
def update_truck(
    truck_id: int,
    truck_data: TruckUpdate,
    db: Session = Depends(get_db)
):
    """
    Update truck details. (Admin)
    """
    truck = db.query(Truck).filter(Truck.id == truck_id).first()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    
    # Check phone uniqueness if changing
    if truck_data.driver_phone and truck_data.driver_phone != truck.driver_phone:
        existing = db.query(Truck).filter(
            Truck.driver_phone == truck_data.driver_phone,
            Truck.id != truck_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Phone number already registered to another truck"
            )
    
    # Update fields
    update_data = truck_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(truck, field, value)
    
    db.commit()
    db.refresh(truck)
    
    return truck


@router.post("/{truck_id}/assign-zone")
def assign_zone(
    truck_id: int,
    zone_id: int,
    db: Session = Depends(get_db)
):
    """
    Assign truck to a zone. (Admin)
    """
    truck = db.query(Truck).filter(Truck.id == truck_id).first()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Check zone not already assigned
    existing = db.query(Truck).filter(
        Truck.zone_id == zone_id,
        Truck.id != truck_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Zone already has truck: {existing.vehicle_number}"
        )
    
    truck.zone_id = zone_id
    db.commit()
    
    return {
        "message": f"Truck assigned to zone '{zone.name}'",
        "truck_id": truck_id,
        "zone_id": zone_id
    }


# ============ DRIVER APP ENDPOINTS ============

@router.post("/login", response_model=DriverLoginResponse)
def driver_login(
    request: DriverLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Driver login with phone number.
    
    Returns truck info and assigned zone.
    """
    truck = db.query(Truck).filter(
        Truck.driver_phone == request.phone
    ).first()
    
    if not truck:
        raise HTTPException(
            status_code=404,
            detail="No truck registered with this phone number"
        )
    
    zone_name = None
    if truck.zone_id:
        zone = db.query(Zone).filter(Zone.id == truck.zone_id).first()
        zone_name = zone.name if zone else None
    
    return DriverLoginResponse(
        truck_id=truck.id,
        vehicle_number=truck.vehicle_number,
        driver_name=truck.driver_name,
        zone_id=truck.zone_id,
        zone_name=zone_name,
        is_active=truck.is_active
    )


@router.post("/{truck_id}/start", response_model=DutyResponse)
def start_duty(
    truck_id: int,
    db: Session = Depends(get_db)
):
    """
    Start duty - Driver presses START button.
    
    Activates tracking and resets alerts for zone users.
    """
    truck = db.query(Truck).filter(Truck.id == truck_id).first()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    
    if truck.is_active:
        return DutyResponse(
            status="active",
            message="Already on duty",
            started_at=truck.duty_started_at
        )
    
    truck.is_active = True
    truck.duty_started_at = datetime.utcnow()
    
    # Reset alerts for all users in this zone
    if truck.zone_id:
        reset_zone_alerts(db, truck.zone_id)
    
    db.commit()
    
    return DutyResponse(
        status="active",
        message="Tracking started! Drive safe.",
        started_at=truck.duty_started_at
    )


@router.post("/{truck_id}/stop", response_model=DutyResponse)
def stop_duty(
    truck_id: int,
    db: Session = Depends(get_db)
):
    """
    Stop duty - Driver presses STOP button.
    
    Deactivates tracking.
    """
    truck = db.query(Truck).filter(Truck.id == truck_id).first()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    
    if not truck.is_active:
        return DutyResponse(
            status="inactive",
            message="Already off duty"
        )
    
    duration = format_duration(truck.duty_started_at)
    
    truck.is_active = False
    db.commit()
    
    return DutyResponse(
        status="inactive",
        message=f"Tracking stopped. Today's duration: {duration}",
        duration=duration
    )


@router.post("/{truck_id}/location")
async def update_location(
    truck_id: int,
    location: LocationUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Update truck location.
    
    Called every 5-30 seconds by driver app.
    Also triggers alert checks for nearby users.
    """
    truck = db.query(Truck).filter(Truck.id == truck_id).first()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    
    # Auto-activate if not active
    if not truck.is_active:
        truck.is_active = True
        truck.duty_started_at = datetime.utcnow()
    
    # Update cached location
    truck.last_lat = location.lat
    truck.last_lng = location.lng
    truck.last_speed = location.speed
    truck.last_heading = location.heading
    truck.last_update = datetime.utcnow()
    
    # Save to history
    db_location = TruckLocation(
        truck_id=truck_id,
        latitude=location.lat,
        longitude=location.lng,
        speed=location.speed,
        heading=location.heading,
        accuracy=location.accuracy,
        captured_at=location.captured_at,
        is_offline_sync=False
    )
    db.add(db_location)
    db.commit()
    
    # Check alerts in background (don't slow down response)
    background_tasks.add_task(process_alerts, truck_id, db)
    
    return {"ok": True, "timestamp": datetime.utcnow().isoformat()}


async def process_alerts(truck_id: int, db: Session):
    """
    Background task to check and send alerts.
    """
    try:
        truck = db.query(Truck).filter(Truck.id == truck_id).first()
        if not truck:
            return
        
        alerts = check_alerts_for_truck(db, truck)
        
        for alert_info in alerts:
            user = db.query(User).filter(User.id == alert_info["user_id"]).first()
            if user:
                await send_alert(db, alert_info, user)
                
    except Exception as e:
        # Log error but don't crash
        import logging
        logging.error(f"Error processing alerts: {e}")


@router.post("/{truck_id}/sync", response_model=LocationSyncResponse)
def sync_offline_locations(
    truck_id: int,
    request: LocationBatchSync,
    db: Session = Depends(get_db)
):
    """
    Sync multiple offline locations.
    
    Called when driver app comes back online after being offline.
    """
    truck = db.query(Truck).filter(Truck.id == truck_id).first()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    
    synced = 0
    failed = 0
    
    # Sort by captured time
    sorted_locations = sorted(request.locations, key=lambda x: x.captured_at)
    
    for loc in sorted_locations:
        try:
            db_location = TruckLocation(
                truck_id=truck_id,
                latitude=loc.lat,
                longitude=loc.lng,
                speed=loc.speed,
                heading=loc.heading,
                accuracy=loc.accuracy,
                captured_at=loc.captured_at,
                is_offline_sync=True
            )
            db.add(db_location)
            synced += 1
        except Exception:
            failed += 1
    
    # Update truck's cached location with most recent
    if sorted_locations:
        last = sorted_locations[-1]
        truck.last_lat = last.lat
        truck.last_lng = last.lng
        truck.last_speed = last.speed
        truck.last_heading = last.heading
        truck.last_update = datetime.utcnow()
        
        # Auto-activate
        if not truck.is_active:
            truck.is_active = True
            truck.duty_started_at = datetime.utcnow()
    
    db.commit()
    
    return LocationSyncResponse(
        synced=synced,
        failed=failed,
        message=f"Synced {synced} locations" + (f", {failed} failed" if failed else "")
    )


@router.get("/{truck_id}/status")
def get_truck_status(
    truck_id: int,
    db: Session = Depends(get_db)
):
    """
    Get truck status (for driver app display).
    """
    truck = db.query(Truck).filter(Truck.id == truck_id).first()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    
    # Count today's locations
    today_start = datetime.combine(date.today(), datetime.min.time())
    location_count = db.query(TruckLocation).filter(
        TruckLocation.truck_id == truck_id,
        TruckLocation.captured_at >= today_start
    ).count()
    
    # Get zone info
    zone_name = None
    if truck.zone_id:
        zone = db.query(Zone).filter(Zone.id == truck.zone_id).first()
        zone_name = zone.name if zone else None
    
    return {
        "truck_id": truck.id,
        "vehicle_number": truck.vehicle_number,
        "zone_name": zone_name,
        "is_active": truck.is_active,
        "duty_started_at": truck.duty_started_at,
        "duration": format_duration(truck.duty_started_at) if truck.duty_started_at else None,
        "last_update": truck.last_update,
        "locations_today": location_count
    }