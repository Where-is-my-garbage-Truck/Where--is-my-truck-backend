# app/main.py
"""
Garbage Truck Tracker API
=========================
Main FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings, get_cors_origins
from app.database import create_tables, engine, get_db
from app.models import Zone, Truck, User, TruckLocation, AlertLog
from app.routes import zones, trucks, users, tracking, websocket


# ============ LOGGING SETUP ============

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============ LIFESPAN ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("🚀 Starting Garbage Truck Tracker API...")
    
    try:
        create_tables()
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        raise
    
    logger.info(f"📊 Database: {settings.DATABASE_URL.split('://')[0]}")
    logger.info(f"🔧 Debug mode: {settings.DEBUG}")
    
    yield
    
    logger.info("👋 Shutting down...")
    engine.dispose()


# ============ CREATE APP ============

app = FastAPI(
    title=settings.APP_NAME,
    description="""
    🚛 Real-time garbage truck tracking system.
    
    Like "Where is my Train" but for garbage trucks!
    
    ## Features
    * **Zone-based tracking** - Each zone has one truck
    * **Real-time updates** - Via polling or WebSocket
    * **Smart alerts** - Push notifications & missed calls
    * **Offline support** - Sync when back online
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# ============ MIDDLEWARE ============

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    if settings.DEBUG:
        logger.debug(f"📥 {request.method} {request.url.path}")
    response = await call_next(request)
    if settings.DEBUG:
        logger.debug(f"📤 {response.status_code}")
    return response


# ============ ERROR HANDLERS ============

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )


# ============ INCLUDE ROUTERS ============

app.include_router(zones.router)
app.include_router(trucks.router)
app.include_router(users.router)
app.include_router(tracking.router)
app.include_router(websocket.router)


# ============ ROOT ENDPOINTS ============

@app.get("/", tags=["Health"])
def root():
    """API root - shows available endpoints."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "zones": "/zones - Zone management (Admin)",
            "trucks": "/truck - Truck & driver management",
            "users": "/user - User registration & settings",
            "tracking": "/track - Live tracking",
            "websocket": "/ws/track/{user_id} - Real-time WebSocket"
        }
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "database": "connected"
    }


@app.get("/config", tags=["Health"])
def get_config():
    """Get public configuration for client apps."""
    return {
        "location_update_interval": settings.LOCATION_UPDATE_INTERVAL,
        "alert_distance_approaching": settings.ALERT_DISTANCE_APPROACHING,
        "alert_distance_arriving": settings.ALERT_DISTANCE_ARRIVING,
        "alert_distance_here": settings.ALERT_DISTANCE_HERE,
        "ws_broadcast_interval": settings.WS_BROADCAST_INTERVAL
    }


# ============ DEBUG ENDPOINTS ============

@app.get("/debug/db", tags=["Debug"])
def debug_database(db: Session = Depends(get_db)):
    """
    Debug endpoint to see database state.
    
    ⚠️ Only available when DEBUG=true
    """
    if not settings.DEBUG:
        return {"error": "Debug endpoint disabled in production"}
    
    zones = db.query(Zone).all()
    trucks = db.query(Truck).all()
    users = db.query(User).all()
    locations_count = db.query(TruckLocation).count()
    alerts_count = db.query(AlertLog).count()
    
    return {
        "zones": [
            {
                "id": z.id, 
                "name": z.name, 
                "bounds": f"({z.min_lat},{z.min_lng}) to ({z.max_lat},{z.max_lng})",
                "active": z.is_active
            } 
            for z in zones
        ],
        "trucks": [
            {
                "id": t.id, 
                "vehicle": t.vehicle_number, 
                "zone_id": t.zone_id, 
                "active": t.is_active,
                "location": f"({t.last_lat},{t.last_lng})" if t.last_lat else "No location"
            } 
            for t in trucks
        ],
        "users": [
            {
                "id": u.id, 
                "name": u.name, 
                "phone": u.phone,
                "home": f"({u.home_lat},{u.home_lng})" if u.home_lat else "No home",
                "zone_id": u.zone_id,
                "alerts": u.alert_type
            } 
            for u in users
        ],
        "stats": {
            "total_zones": len(zones),
            "total_trucks": len(trucks),
            "total_users": len(users),
            "total_locations": locations_count,
            "total_alerts": alerts_count
        }
    }


@app.delete("/debug/reset", tags=["Debug"])
def reset_database(confirm: bool = False, db: Session = Depends(get_db)):
    """
    Reset database (delete all data).
    
    ⚠️ DANGEROUS! Requires confirm=true parameter.
    """
    if not settings.DEBUG:
        return {"error": "Debug endpoint disabled in production"}
    
    if not confirm:
        return {"error": "Pass confirm=true to reset database"}
    
    # Delete in order (foreign key constraints)
    db.query(AlertLog).delete()
    db.query(TruckLocation).delete()
    db.query(User).delete()
    db.query(Truck).delete()
    db.query(Zone).delete()
    db.commit()
    
    return {"message": "Database reset complete", "status": "empty"}