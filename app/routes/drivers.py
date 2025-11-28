# app/routes/drivers.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Driver
from app.schemas import DriverCreate, DriverResponse

router = APIRouter(prefix="/drivers", tags=["Drivers"])


# ================== REGISTER DRIVER ==================
@router.post("/register", response_model=DriverResponse)
def register_driver(driver: DriverCreate, db: Session = Depends(get_db)):
    """Register a new driver"""

    clean_phone = driver.phone.strip()
    clean_vehicle = driver.vehicle_number.strip()
    clean_name = driver.name.strip()

    # Check if phone already exists
    existing_phone = db.query(Driver).filter(Driver.phone == clean_phone).first()
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    # Check if vehicle number already exists
    existing_vehicle = db.query(Driver).filter(
        Driver.vehicle_number == clean_vehicle
    ).first()
    if existing_vehicle:
        raise HTTPException(status_code=400, detail="Vehicle number already registered")
    
    db_driver = Driver(
        name=clean_name,
        phone=clean_phone,
        vehicle_number=clean_vehicle
    )
    db.add(db_driver)
    db.commit()
    db.refresh(db_driver)
    return db_driver


# ================== GET DRIVER BY PHONE (place above ID) ==================
@router.get("/phone/{phone}", response_model=DriverResponse)
def get_driver_by_phone(phone: str, db: Session = Depends(get_db)):
    """Get driver by phone (for login)"""

    clean_phone = phone.strip()

    driver = db.query(Driver).filter(Driver.phone == clean_phone).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver


# ================== GET DRIVER BY ID ==================
@router.get("/{driver_id}", response_model=DriverResponse)
def get_driver(driver_id: int, db: Session = Depends(get_db)):
    """Get driver by ID"""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver


# ================== SET DRIVER ONLINE ==================
@router.put("/{driver_id}/online", response_model=dict)
def set_driver_online(driver_id: int, db: Session = Depends(get_db)):
    """Set driver status to online"""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    driver.is_online = True
    db.commit()
    return {"message": "Driver is now online", "driver_id": driver_id}


# ================== SET DRIVER OFFLINE ==================
@router.put("/{driver_id}/offline", response_model=dict)
def set_driver_offline(driver_id: int, db: Session = Depends(get_db)):
    """Set driver status to offline"""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    driver.is_online = False
    db.commit()
    return {"message": "Driver is now offline", "driver_id": driver_id}


# ================== LIST DRIVERS ==================
@router.get("/", response_model=List[DriverResponse])
def list_drivers(
    online_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all drivers, optionally filter by online status"""

    query = db.query(Driver)
    if online_only:
        query = query.filter(Driver.is_online == True)
    
    drivers = query.offset(skip).limit(limit).all()
    return drivers
