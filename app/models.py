# app/models.py
"""
Database Models
===============
All SQLAlchemy models for the garbage truck tracking system.

Tables:
    - Zone: Service areas/wards
    - Truck: Garbage trucks with drivers
    - TruckLocation: GPS location history
    - User: Residents who track trucks
    - AlertLog: Track sent alerts (avoid duplicates)

Relationships:
    Zone 1:1 Truck (one truck per zone)
    Zone 1:N User (many users in a zone)
    Truck 1:N TruckLocation (location history)
    User 1:N AlertLog (alert history)
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    ForeignKey, Date, Time, Text, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Zone(Base):
    """
    Service Zone / Ward
    
    Each zone has:
    - A boundary (rectangle defined by min/max lat/lng)
    - One assigned truck
    - Many users living in it
    """
    __tablename__ = "zones"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    city = Column(String(100), default="")
    
    # Zone boundary (rectangle)
    # Southwest corner
    min_lat = Column(Float, nullable=False)
    min_lng = Column(Float, nullable=False)
    # Northeast corner
    max_lat = Column(Float, nullable=False)
    max_lng = Column(Float, nullable=False)
    
    # Typical schedule (informational)
    typical_start_time = Column(Time, nullable=True)
    typical_end_time = Column(Time, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    truck = relationship("Truck", back_populates="zone", uselist=False)
    users = relationship("User", back_populates="zone")
    
    def __repr__(self):
        return f"<Zone {self.name}>"
    
    def contains_point(self, lat: float, lng: float) -> bool:
        """Check if a point is inside this zone."""
        return (self.min_lat <= lat <= self.max_lat and
                self.min_lng <= lng <= self.max_lng)


class Truck(Base):
    """
    Garbage Truck
    
    Each truck has:
    - Vehicle number (unique identifier)
    - Assigned driver (phone for login)
    - Assigned zone
    - Current location (cached for fast access)
    """
    __tablename__ = "trucks"
    
    id = Column(Integer, primary_key=True, index=True)
    vehicle_number = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=True)  # Friendly name like "Truck 1"
    
    # Assigned zone (one truck per zone)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True, unique=True)
    
    # Driver information
    driver_name = Column(String(100), nullable=True)
    driver_phone = Column(String(20), unique=True, nullable=False, index=True)
    
    # Current status
    is_active = Column(Boolean, default=False)  # On duty right now?
    duty_started_at = Column(DateTime, nullable=True)
    
    # Cached latest location (for fast queries without joining)
    last_lat = Column(Float, nullable=True)
    last_lng = Column(Float, nullable=True)
    last_speed = Column(Float, default=0)       # km/h
    last_heading = Column(Float, default=0)     # 0-360 degrees
    last_update = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    zone = relationship("Zone", back_populates="truck")
    locations = relationship("TruckLocation", back_populates="truck", 
                            cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Truck {self.vehicle_number}>"


class TruckLocation(Base):
    """
    Truck Location History
    
    Stores every GPS update from the driver app.
    Used for:
    - Drawing route on map
    - Analytics
    - Debugging
    """
    __tablename__ = "truck_locations"
    
    id = Column(Integer, primary_key=True, index=True)
    truck_id = Column(Integer, ForeignKey("trucks.id", ondelete="CASCADE"), 
                      nullable=False)
    
    # GPS data
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed = Column(Float, default=0)            # km/h
    heading = Column(Float, default=0)          # 0-360 degrees
    accuracy = Column(Float, nullable=True)     # GPS accuracy in meters
    
    # Timestamps
    captured_at = Column(DateTime, nullable=False)  # When GPS captured on device
    synced_at = Column(DateTime, server_default=func.now())  # When server received
    
    # Offline sync flag
    is_offline_sync = Column(Boolean, default=False)
    
    # Relationship
    truck = relationship("Truck", back_populates="locations")
    
    # Index for efficient queries
    __table_args__ = (
        Index('idx_truck_location_time', 'truck_id', 'captured_at'),
    )
    
    def __repr__(self):
        return f"<TruckLocation {self.latitude},{self.longitude}>"


class User(Base):
    """
    User / Resident
    
    Users who want to track garbage trucks.
    Each user has:
    - Phone number (for login and missed call alerts)
    - Home location (to calculate distance from truck)
    - Alert preferences
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    
    # Home location
    home_lat = Column(Float, nullable=True)
    home_lng = Column(Float, nullable=True)
    home_address = Column(String(500), nullable=True)
    
    # Auto-assigned zone based on home location
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    
    # Alert preferences
    alert_enabled = Column(Boolean, default=True)
    alert_distance = Column(Integer, default=500)  # meters
    alert_type = Column(String(20), default="push")  # push / missed_call / both / sound
    
    # Push notification token (Firebase)
    fcm_token = Column(Text, nullable=True)
    
    # For tracking alert state (to show in app)
    last_alert_type = Column(String(20), nullable=True)  # approaching/arriving/here
    last_alert_at = Column(DateTime, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    zone = relationship("Zone", back_populates="users")
    alert_logs = relationship("AlertLog", back_populates="user",
                             cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.name}>"


class AlertLog(Base):
    """
    Alert Log
    
    Tracks which alerts have been sent to avoid duplicates.
    One alert per type per day per user.
    """
    __tablename__ = "alert_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), 
                     nullable=False)
    truck_id = Column(Integer, ForeignKey("trucks.id", ondelete="CASCADE"), 
                      nullable=False)
    
    # Alert details
    alert_date = Column(Date, nullable=False)
    alert_type = Column(String(20), nullable=False)  # approaching / arriving / here
    
    # Context when alert was sent
    distance_meters = Column(Integer, nullable=True)
    truck_lat = Column(Float, nullable=True)
    truck_lng = Column(Float, nullable=True)
    
    sent_at = Column(DateTime, server_default=func.now())
    
    # Delivery status
    delivered = Column(Boolean, default=True)
    delivery_method = Column(String(20), nullable=True)  # push / missed_call / sound
    
    # Relationship
    user = relationship("User", back_populates="alert_logs")
    
    # Unique constraint: one alert per type per day per user per truck
    __table_args__ = (
        Index('idx_alert_unique', 'user_id', 'truck_id', 'alert_date', 'alert_type', 
              unique=True),
    )
    
    def __repr__(self):
        return f"<AlertLog {self.alert_type} for User {self.user_id}>"