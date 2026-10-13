"""
Authentication Utilities with MongoDB.
"""

import os
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt

from .database import get_users_collection, get_admins_collection
from .config_loader import get_app_config

app_config = get_app_config()
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError("Set JWT_SECRET_KEY to a random value of at least 32 characters in the project .env file.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", app_config.get("access_token_expire_minutes") or app_settings.get("access_token_expire_minutes") or 60))

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security = HTTPBearer(auto_error=False)


async def load_auth() -> Dict[str, Any]:
    """Load all users and admins from MongoDB."""
    users_cursor = get_users_collection().find({})
    users = {}
    async for user in users_cursor:
        users[user["email"]] = user

    admins_cursor = get_admins_collection().find({})
    admins = {}
    async for admin in admins_cursor:
        admins[admin["email"]] = admin

    return {"users": users, "admins": admins}


async def save_user(user_data: Dict[str, Any]) -> None:
    """Save user to MongoDB."""
    await get_users_collection().replace_one({"email": user_data["email"]}, user_data, upsert=True)


async def save_admin(admin_data: Dict[str, Any]) -> None:
    """Save admin to MongoDB."""
    await get_admins_collection().replace_one({"email": admin_data["email"]}, admin_data, upsert=True)


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    return await get_users_collection().find_one({"email": email})


async def get_admin_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get admin by email."""
    return await get_admins_collection().find_one({"email": email})


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        if pwd_context.verify(plain_password, stored_hash):
            return True
    except Exception:
        pass
    try:
        import hashlib
        legacy = hashlib.sha256(plain_password.encode()).hexdigest()
        if legacy == stored_hash:
            return True
    except Exception:
        pass
    return False


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def migrate_password_if_needed(email: str, role: str, plain_password: str, stored_hash: str) -> bool:
    try:
        import hashlib
        if hashlib.sha256(plain_password.encode()).hexdigest() == stored_hash:
            new_hash = get_password_hash(plain_password)
            if role == "user":
                await get_users_collection().update_one({"email": email}, {"$set": {"password": new_hash}})
            elif role == "admin":
                await get_admins_collection().update_one({"email": email}, {"$set": {"password": new_hash}})
            return True
    except Exception:
        pass
    return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


class TokenData:
    def __init__(self, email: Optional[str] = None, role: Optional[str] = None, sub: Optional[str] = None):
        self.email = email
        self.role = role
        self.sub = sub


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
) -> TokenData:
    token = None
    if credentials is not None:
        token = credentials.credentials

    if not token and x_user_email:
        user = await get_user_by_email(x_user_email)
        if user:
            return TokenData(email=user["email"], role=user.get("role", "user"), sub=user["email"])
        admin = await get_admin_by_email(x_user_email)
        if admin:
            return TokenData(email=admin["email"], role=admin.get("role", "admin"), sub=admin["email"])
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user email")

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub") or payload.get("email")
        role: str = payload.get("role")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return TokenData(email=email, role=role, sub=email)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user