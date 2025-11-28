# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import engine, Base
from app.routes import users, drivers, tracking


# ----------- Optional: Better grouping in Swagger -----------
tags_metadata = [
    {"name": "Users", "description": "User registration and user account APIs"},
    {"name": "Drivers", "description": "Driver registration, login, and status APIs"},
    {"name": "Tracking", "description": "Real-time tracking, location updates, and map APIs"},
]


# ----------- Lifespan Event (Runs on startup/shutdown) -----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    yield
    print("👋 API shutdown complete")


# ----------- FastAPI Application -----------
app = FastAPI(
    title="Garbage Truck Tracker API",
    description="Real-time garbage truck tracking system similar to Uber.",
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan
)


# ----------- CORS Middleware -----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # Allow all for local/testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------- Routers -----------
app.include_router(users.router)
app.include_router(drivers.router)
app.include_router(tracking.router)


# ----------- Root Endpoint -----------
@app.get("/")
def root():
    return {
        "message": "🚛 Garbage Truck Tracker API",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "users": "/users",
            "drivers": "/drivers",
            "tracking": "/tracking",
        }
    }


# ----------- Health Check -----------
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "garbage-tracker"}


# ----------- Ping (optional for uptime monitoring) -----------
@app.get("/ping")
def ping():
    return {"ping": "pong"}
