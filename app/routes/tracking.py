# app/routes/tracking.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
import math

from app.database import get_db
from app.models import Driver, DriverLocation
from app.schemas import LocationUpdate, LocationResponse, LocationHistory, BatchLocationUpdate

router = APIRouter(prefix="/tracking", tags=["Tracking"])


# ----------------- Helpers -----------------

def get_latest_location(db: Session, driver_id: int):
    return db.query(DriverLocation).filter(
        DriverLocation.driver_id == driver_id
    ).order_by(desc(DriverLocation.timestamp)).first()


def haversine(lat1, lon1, lat2, lon2):
    """Distance between 2 coordinates in KM"""
    lat1, lon1 = math.radians(lat1), math.radians(lon1)
    lat2, lon2 = math.radians(lat2), math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return 6371 * c  # Earth radius


# ----------------- DRIVER SENDS LOCATION -----------------

@router.post("/location")
def update_location(location: LocationUpdate, db: Session = Depends(get_db)):
    """Driver app sends real-time location"""

    driver = db.query(Driver).filter(Driver.id == location.driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    # Mark online
    driver.is_online = True

    db_location = DriverLocation(
        driver_id=location.driver_id,
        latitude=location.latitude,
        longitude=location.longitude,
        heading=location.heading or 0,
        speed=location.speed or 0
    )

    db.add(db_location)
    db.commit()
    db.refresh(db_location)

    return {
        "success": True,
        "message": "Location updated",
        "timestamp": db_location.timestamp
    }


@router.post("/location/batch")
def batch_update_location(batch: BatchLocationUpdate, db: Session = Depends(get_db)):
    """
    Driver syncs multiple locations at once (offline mode)
    """

    driver = db.query(Driver).filter(Driver.id == batch.driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    driver.is_online = True

    count = 0
    for loc in batch.locations:
        db_loc = DriverLocation(
            driver_id=batch.driver_id,
            latitude=loc.latitude,
            longitude=loc.longitude,
            heading=loc.heading or 0,
            speed=loc.speed or 0
        )
        db.add(db_loc)
        count += 1

    db.commit()

    return {"success": True, "message": f"Synced {count} locations", "count": count}


# ----------------- USER FETCHES LIVE DATA -----------------

@router.get("/drivers/live", response_model=List[LocationResponse])
def get_all_live_drivers(db: Session = Depends(get_db)):
    """Return all online drivers with their last known location"""

    drivers = db.query(Driver).filter(Driver.is_online == True).all()

    results = []
    for driver in drivers:
        latest = get_latest_location(db, driver.id)
        if latest:
            results.append(LocationResponse(
                driver_id=driver.id,
                driver_name=driver.name,
                vehicle_number=driver.vehicle_number,
                latitude=latest.latitude,
                longitude=latest.longitude,
                heading=latest.heading,
                speed=latest.speed,
                timestamp=latest.timestamp,
                is_online=driver.is_online
            ))

    return results


@router.get("/driver/{driver_id}/live", response_model=LocationResponse)
def get_driver_live_location(driver_id: int, db: Session = Depends(get_db)):
    """Get real-time location of a specific driver"""

    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    latest = get_latest_location(db, driver_id)
    if not latest:
        raise HTTPException(status_code=404, detail="No location data available")

    return LocationResponse(
        driver_id=driver.id,
        driver_name=driver.name,
        vehicle_number=driver.vehicle_number,
        latitude=latest.latitude,
        longitude=latest.longitude,
        heading=latest.heading,
        speed=latest.speed,
        timestamp=latest.timestamp,
        is_online=driver.is_online
    )


@router.get("/driver/{driver_id}/history", response_model=List[LocationHistory])
def get_driver_location_history(
    driver_id: int,
    minutes: int = Query(default=30, le=1440),
    db: Session = Depends(get_db)
):
    """Return driver route history for last X minutes"""

    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    cutoff = datetime.utcnow() - timedelta(minutes=minutes)

    locations = db.query(DriverLocation).filter(
        DriverLocation.driver_id == driver_id,
        DriverLocation.timestamp >= cutoff
    ).order_by(DriverLocation.timestamp).all()

    return locations


# ----------------- NEARBY DRIVERS -----------------

@router.get("/drivers/nearby")
def get_nearby_drivers(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=5, le=50),
    db: Session = Depends(get_db)
):
    """Return drivers within X km radius (Uber-like search)"""

    online_drivers = db.query(Driver).filter(Driver.is_online == True).all()

    nearby = []
    for driver in online_drivers:
        latest = get_latest_location(db, driver.id)
        if latest:
            dist = haversine(latitude, longitude, latest.latitude, latest.longitude)
            if dist <= radius_km:
                nearby.append({
                    "driver_id": driver.id,
                    "driver_name": driver.name,
                    "vehicle_number": driver.vehicle_number,
                    "latitude": latest.latitude,
                    "longitude": latest.longitude,
                    "distance_km": round(dist, 2),
                    "heading": latest.heading,
                    "speed": latest.speed,
                    "is_online": driver.is_online
                })

    nearby.sort(key=lambda x: x["distance_km"])
    return nearby
