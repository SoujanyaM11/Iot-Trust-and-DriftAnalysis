"""MongoDB database connection and collection accessors for SentinelTrust."""
import os
from typing import Any, Optional

from pymongo import ASCENDING, DESCENDING, IndexModel, MongoClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging

logger = logging.getLogger("sentineltrust")

# Global database client
_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None
_sync_client: Optional[MongoClient] = None
_sync_db = None
_db_mode = "unknown"


async def init_mongodb(uri: str = None, db_name: str = None):
    """Initialize MongoDB connection.

    MongoDB is required; the API does not start in a file-backed fallback mode.
    """
    global _client, _db, _sync_client, _sync_db, _db_mode

    from .config_loader import get_config
    config = get_config()
    mongo_uri = uri or os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or config.get("mongodb", {}).get("uri") or "mongodb://localhost:27017/sentineltrust"
    database_name = db_name or os.getenv("MONGODB_DATABASE") or os.getenv("MONGO_DATABASE") or os.getenv("MONGODB_DB") or config.get("mongodb", {}).get("database") or "sentineltrust"
    try:
        if not mongo_uri or not database_name:
            raise ValueError("MongoDB URI and database name must both be configured")
        _client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
        _db = _client[database_name]
        await _db.command("ping")
        await _create_indexes()
        _sync_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        _sync_db = _sync_client[database_name]
        _sync_db.command("ping")
        _db_mode = "mongodb"
        logger.info("MongoDB connected successfully: %s", database_name)
        return _db
    except Exception as exc:
        if _client is not None:
            _client.close()
            _client = None
        if _sync_client is not None:
            _sync_client.close()
            _sync_client = None
            _sync_db = None
        _db = None
        logger.error("MongoDB connection failed for %s: %s", database_name, exc)
        raise RuntimeError(
            "MongoDB connection failed. Start your MongoDB service and set MONGODB_URI "
            "and MONGODB_DATABASE in the project .env file or config/config.yaml."
        ) from exc


async def _create_indexes():
    """Create database indexes for performance."""
    if _db is None:
        return
    collections = _db

    await collections.users.create_indexes([
        IndexModel([("email", ASCENDING)], unique=True),
    ])
    await collections.admins.create_indexes([
        IndexModel([("email", ASCENDING)], unique=True),
    ])
    await collections.devices.create_indexes([
        IndexModel([("user_email", ASCENDING), ("id", ASCENDING)], unique=True),
        IndexModel([("user_email", ASCENDING)]),
    ])
    await collections.trust_scores.create_indexes([
        IndexModel([("user_email", ASCENDING), ("device_id", ASCENDING), ("recorded_at", DESCENDING)]),
        IndexModel([("user_email", ASCENDING), ("recorded_at", DESCENDING)]),
    ])
    await collections.alerts.create_indexes([
        IndexModel([("user_email", ASCENDING), ("device_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("resolved", ASCENDING), ("created_at", DESCENDING)]),
    ])
    await collections.policy_violations.create_indexes([
        IndexModel([("user_email", ASCENDING), ("device_id", ASCENDING), ("detected_at", DESCENDING)]),
    ])
    await collections.notifications.create_indexes([
        IndexModel([("to_email", ASCENDING), ("sent_at", DESCENDING)]),
    ])
    await collections.smtp_config.create_indexes([
        IndexModel([("username", ASCENDING)], unique=True),
    ])
    await collections.user_states.create_indexes([
        IndexModel([("user_email", ASCENDING)], unique=True),
    ])
    logger.info("MongoDB indexes created")


def get_db() -> Any:
    """Get the initialized MongoDB database instance."""
    if _db is None:
        raise RuntimeError("MongoDB is not initialized. Check connectivity and start the app through its lifespan.")
    return _db


def get_sync_db() -> Any:
    """Get the synchronous MongoDB database used by the synchronous trust engine."""
    if _sync_db is not None:
        return _sync_db
    raise RuntimeError("MongoDB is not initialized. Start the application lifespan before using the database.")


async def close_mongodb():
    """Close MongoDB connection."""
    global _client, _db, _sync_client, _sync_db, _db_mode
    if _client:
        _client.close()
        _client = None
    if _sync_client:
        _sync_client.close()
        _sync_client = None
    _sync_db = None
    _db = None
    _db_mode = "unknown"
    logger.info("MongoDB connection closed")


# Collection accessors
def get_users_collection():
    return get_db().users

def get_admins_collection():
    return get_db().admins

def get_devices_collection():
    return get_db().devices

def get_trust_scores_collection():
    return get_db().trust_scores

def get_alerts_collection():
    return get_db().alerts

def get_policy_violations_collection():
    return get_db().policy_violations

def get_notifications_collection():
    return get_db().notifications

def get_smtp_config_collection():
    return get_db().smtp_config

def get_user_states_collection():
    return get_db().user_states

def get_sync_user_states_collection():
    return get_sync_db().user_states

def get_sync_notifications_collection():
    return get_sync_db().notifications