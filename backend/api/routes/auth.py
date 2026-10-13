"""SentinelTrust - Auth Routes.

User registration/login and admin-only dashboard access.
"""

import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...auth_utils import (
    load_auth,
    save_user,
    save_admin,
    verify_password,
    get_password_hash,
    migrate_password_if_needed,
    create_access_token,
    require_admin,
    get_user_by_email,
    get_admin_by_email,
    TokenData,
)
from ...database import get_user_states_collection, get_notifications_collection

router = APIRouter()


class UserRegister(BaseModel):
    name: str
    email: str
    phone: str
    password: str


class AdminRegister(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str
    role: str


@router.post("/register/user")
async def register_user(body: UserRegister):
    store = await load_auth()
    if body.email in store["users"]:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_data = {
        "name": body.name,
        "email": body.email,
        "phone": body.phone,
        "password": get_password_hash(body.password),
        "role": "user",
        "created_at": time.time(),
    }
    await save_user(user_data)
    return {"status": "registered", "role": "user", "name": body.name, "email": body.email}


@router.post("/register/admin")
async def register_admin(body: AdminRegister):
    store = await load_auth()
    if len(store["admins"]) >= 1:
        raise HTTPException(status_code=400, detail="An admin account already exists. Only one admin is allowed.")

    admin_data = {
        "name": body.name,
        "email": body.email,
        "password": get_password_hash(body.password),
        "role": "admin",
        "created_at": time.time(),
    }
    await save_admin(admin_data)
    return {"status": "registered", "role": "admin", "name": body.name, "email": body.email}


@router.post("/login")
async def login(body: LoginRequest):
    store = await load_auth()
    if body.role == "user":
        user = store["users"].get(body.email)
        if not user or not verify_password(body.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        await migrate_password_if_needed(body.email, "user", body.password, user["password"])
        access_token = create_access_token({"sub": body.email, "email": body.email, "role": "user"})
        return {
            "status": "ok",
            "token": access_token,
            "role": "user",
            "name": user["name"],
            "email": user["email"],
            "phone": user.get("phone", ""),
        }

    if body.role == "admin":
        admin = store["admins"].get(body.email)
        if not admin or not verify_password(body.password, admin["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        await migrate_password_if_needed(body.email, "admin", body.password, admin["password"])
        access_token = create_access_token({"sub": body.email, "email": body.email, "role": "admin"})
        return {
            "status": "ok",
            "token": access_token,
            "role": "admin",
            "name": admin["name"],
            "email": admin["email"],
        }

    raise HTTPException(status_code=400, detail="Invalid role")


@router.get("/admin/dashboard-data")
async def admin_dashboard_data(current_user: TokenData = Depends(require_admin)):
    auth = await load_auth()
    users = []
    for user in auth["users"].values():
        users.append({
            "name": user["name"],
            "email": user["email"],
            "phone": user.get("phone", ""),
            "joined": time.strftime("%Y-%m-%d %H:%M", time.localtime(user.get("created_at", 0))),
        })

    devices = []
    baselines = []
    states_cursor = get_user_states_collection().find({})
    async for state in states_cursor:
        owner = state.get("user_email", "")
        for device in state.get("devices", {}).values():
            devices.append({
                "id": device["id"],
                "name": device["name"],
                "type": device["type"],
                "ip": device["ip"],
                "has_baseline": device.get("has_baseline", False),
                "test_count": device.get("test_count", 0),
                "owner": owner,
                "registered_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(device.get("registered_at", 0))),
            })
        for device_id, baseline in state.get("baselines", {}).items():
            baselines.append({
                "device_id": device_id,
                "owner": owner,
                "n_samples": baseline.get("n_samples", 0),
                "trained_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(baseline.get("trained_at", 0))),
                "features": baseline.get("feature_cols", []),
            })

    notification_cursor = get_notifications_collection().find({}).sort("sent_at", -1).limit(50)
    notifications = []
    async for notification in notification_cursor:
        notifications.append({
            "device_id": notification.get("device_id"),
            "to_email": notification.get("to_email"),
            "score": notification.get("score"),
            "level": notification.get("level"),
            "explanation": notification.get("explanation"),
            "attack_type": notification.get("attack_type"),
            "suspicious_ips": notification.get("suspicious_ips", []),
            "sent_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(notification.get("sent_at", 0))),
            "email_sent": notification.get("email_sent", False),
        })

    return {
        "users": users,
        "devices": devices,
        "baselines": baselines,
        "notifications": list(reversed(notifications)),
        "summary": {
            "total_users": len(users),
            "total_devices": len(devices),
            "total_alerts": len(notifications),
            "devices_with_baseline": sum(1 for device in devices if device["has_baseline"]),
        },
    }


@router.get("/users")
async def list_users():
    store = await load_auth()
    return {"users": [{"name": user["name"], "email": user["email"], "phone": user.get("phone", "")} for user in store["users"].values()]}


@router.get("/admin/users-full")
async def admin_users_full(current_user: TokenData = Depends(require_admin)):
    auth = await load_auth()
    users = []
    for user in auth["users"].values():
        users.append({
            "name": user["name"],
            "email": user["email"],
            "phone": user.get("phone", ""),
            "role": user.get("role", "user"),
            "joined": time.strftime("%Y-%m-%d %H:%M", time.localtime(user.get("created_at", 0))),
        })
    return {"users": users}


@router.get("/admin/exists")
async def admin_exists():
    store = await load_auth()
    return {"exists": len(store["admins"]) >= 1}
