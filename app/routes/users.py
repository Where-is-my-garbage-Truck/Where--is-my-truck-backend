# app/routes/users.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""

    clean_phone = user.phone.strip()
    clean_name = user.name.strip()

    # Check if phone already exists
    existing = db.query(User).filter(User.phone == clean_phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    db_user = User(name=clean_name, phone=clean_phone)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/phone/{phone}", response_model=UserResponse)
def get_user_by_phone(phone: str, db: Session = Depends(get_db)):
    """Get user by phone (login-friendly)"""

    clean_phone = phone.strip()

    user = db.query(User).filter(User.phone == clean_phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/", response_model=List[UserResponse])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all users"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users
