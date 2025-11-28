# app/routes/__init__.py
"""
Routes Package
==============
All API route modules.
"""

from app.routes import zones, trucks, users, tracking, websocket

__all__ = ["zones", "trucks", "users", "tracking", "websocket"]