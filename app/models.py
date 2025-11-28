# app/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """Normal users who track garbage trucks"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True)


class Driver(Base):
    """Garbage truck drivers"""
    __tablename__ = "drivers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    vehicle_number = Column(String(20), unique=True, nullable=False)
    is_online = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationship to locations
    locations = relationship(
        "DriverLocation",
        back_populates="driver",
        cascade="all, delete-orphan"
    )


class DriverLocation(Base):
    """Store driver location history"""
    __tablename__ = "driver_locations"
    
    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    heading = Column(Float, default=0)
    speed = Column(Float, default=0)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    driver = relationship("Driver", back_populates="locations")
