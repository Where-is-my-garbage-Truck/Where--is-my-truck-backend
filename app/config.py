# app/config.py

"""
Configuration Management
========================
All settings in one place. Uses environment variables for security.
Easy to switch between development (SQLite) and production (PostgreSQL).

Usage:
    from app.config import settings
    print(settings.DATABASE_URL)
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application Settings
    
    All settings can be overridden via environment variables.
    Example: DATABASE_URL=postgresql://... python main.py
    """
    
    # ============ APP INFO ============
    APP_NAME: str = "Garbage Truck Tracker"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    
    # ============ DATABASE ============
    # SQLite (default for development)
    DATABASE_URL: str = "sqlite:///./garbage_tracker.db"
    
    # ============ TRACKING SETTINGS ============
    LOCATION_UPDATE_INTERVAL: int = 10
    LOCATION_STALE_THRESHOLD: int = 60
    
    # ============ ALERT SETTINGS ============
    DEFAULT_ALERT_DISTANCE: int = 500
    ALERT_DISTANCE_APPROACHING: int = 1000
    ALERT_DISTANCE_ARRIVING: int = 500
    ALERT_DISTANCE_HERE: int = 100
    
    # ============ ETA SETTINGS ============
    AVG_TRUCK_SPEED: float = 12.0
    TRAFFIC_PEAK_MULTIPLIER: float = 1.5
    TRAFFIC_NORMAL_MULTIPLIER: float = 1.2
    
    # ============ NOTIFICATION SETTINGS ============
    FCM_SERVER_KEY: Optional[str] = None
    MISSED_CALL_API_KEY: Optional[str] = None
    MISSED_CALL_API_URL: Optional[str] = None
    
    # ============ WEBSOCKET SETTINGS ============
    WS_BROADCAST_INTERVAL: int = 3
    
    # ============ CORS ============
    CORS_ORIGINS: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()


# ============ HELPER FUNCTIONS ============

def is_sqlite() -> bool:
    return settings.DATABASE_URL.startswith("sqlite")


def is_postgres() -> bool:
    return settings.DATABASE_URL.startswith("postgresql")


def get_cors_origins() -> list:
    """Return allowed CORS origins."""
    if settings.CORS_ORIGINS == "*":
        return ["*"]
    return [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
