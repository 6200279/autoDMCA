#!/usr/bin/env python3
"""
Minimal FastAPI backend with just authentication functionality
For testing the login fixes
"""
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError

# Environment configuration
DEBUG = True
SECRET_KEY = "dev-secret-key-for-testing-12345"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Setup
app = FastAPI(title="AutoDMCA Minimal API", version="1.0.0")
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:13000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: Optional[bool] = False

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: Optional[Dict[str, Any]] = None

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool

# Utility functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# Mock users matching frontend credentials
MOCK_USERS = {
    "admin@autodmca.com": {
        "id": "admin_user_1",
        "email": "admin@autodmca.com", 
        "full_name": "Admin User",
        "password": "admin123",
        "is_active": True,
        "is_superuser": True,
        "is_verified": True
    },
    "user@example.com": {
        "id": "regular_user_1",
        "email": "user@example.com",
        "full_name": "Regular User", 
        "password": "user1234",
        "is_active": True,
        "is_superuser": False,
        "is_verified": True
    },
    "dev@localhost": {
        "id": "dev_user_1",
        "email": "dev@localhost",
        "full_name": "Development User",
        "password": "DevPassword123!",
        "is_active": True,
        "is_superuser": False,
        "is_verified": True
    }
}

# Authentication endpoints
@app.post("/api/v1/auth/login", response_model=Token)
async def login(credentials: LoginRequest):
    """Login endpoint with mock authentication"""
    print(f"Login attempt: {credentials.email}")
    
    # Get mock user
    user = MOCK_USERS.get(credentials.email)
    if not user or user["password"] != credentials.password:
        print(f"Login failed for {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    print(f"Login successful for {credentials.email}")
    
    # Create tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    if credentials.remember_me:
        access_token_expires = timedelta(days=7)
    
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"]},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user["id"]})
    
    # Prepare user data
    user_data = {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "company": "AutoDMCA" if user["is_superuser"] else "Test Company",
        "phone": "+1234567890",
        "bio": "System Administrator" if user["is_superuser"] else "Test User",
        "avatar_url": None,
        "is_active": user["is_active"],
        "is_verified": user["is_verified"],
        "is_superuser": user["is_superuser"],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "last_login": datetime.utcnow().isoformat() + "Z"
    }
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
        user=user_data
    )

@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user info"""
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = payload.get("sub")
    # Find user by ID
    for user in MOCK_USERS.values():
        if user["id"] == user_id:
            return UserResponse(
                id=user["id"],
                email=user["email"],
                full_name=user["full_name"],
                is_active=user["is_active"],
                is_superuser=user["is_superuser"]
            )
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )

@app.get("/")
async def root():
    """Health check"""
    return {"message": "AutoDMCA Minimal API", "status": "running", "version": "1.0.0"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    print("Starting AutoDMCA Minimal Backend...")
    print("Available test credentials:")
    print("- admin@autodmca.com / admin123 (Admin)")
    print("- user@example.com / user1234 (User)")
    print("- dev@localhost / DevPassword123! (Legacy)")
    uvicorn.run(app, host="0.0.0.0", port=8002)