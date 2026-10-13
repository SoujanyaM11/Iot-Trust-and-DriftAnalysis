import os
import yaml
from typing import Dict, Any
from dotenv import load_dotenv

_config_cache: Dict[str, Any] = {}


def _read_env_value(*keys: str) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value is not None and value != "":
            return value
    return None


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply environment overrides for deployment configuration."""
    mongodb = config.setdefault("mongodb", {})
    mongo_uri = _read_env_value("MONGODB_URI", "MONGO_URI")
    if mongo_uri:
        mongodb["uri"] = mongo_uri
    mongo_db = _read_env_value("MONGODB_DATABASE", "MONGO_DATABASE", "MONGODB_DB")
    if mongo_db:
        mongodb["database"] = mongo_db

    app_cfg = config.setdefault("app", {})
    secret_key = _read_env_value("JWT_SECRET_KEY", "APP_SECRET_KEY")
    if secret_key:
        app_cfg["secret_key"] = secret_key
    token_expire = _read_env_value("ACCESS_TOKEN_EXPIRE_MINUTES")
    if token_expire:
        app_cfg["access_token_expire_minutes"] = int(token_expire)
    cors_origins = _read_env_value("CORS_ORIGINS")
    if cors_origins:
        app_cfg["cors_origins"] = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

    smtp_cfg = config.setdefault("email", {})
    smtp_host = _read_env_value("SMTP_HOST")
    if smtp_host:
        smtp_cfg["smtp_host"] = smtp_host
    smtp_port = _read_env_value("SMTP_PORT")
    if smtp_port:
        smtp_cfg["smtp_port"] = int(smtp_port)
    smtp_user = _read_env_value("SMTP_USERNAME")
    if smtp_user:
        smtp_cfg["username"] = smtp_user
    smtp_from = _read_env_value("SMTP_FROM_EMAIL")
    if smtp_from:
        smtp_cfg["from_email"] = smtp_from

    return config


def _load_config() -> Dict[str, Any]:
    """Load configuration from ``config/config.yaml`` relative to the project root.
    Returns an empty dict if the file is missing.
    """
    global _config_cache
    if _config_cache:
        return _config_cache

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    load_dotenv(os.path.join(project_root, ".env"))
    config_path = os.path.join(project_root, "config", "config.yaml")
    if not os.path.exists(config_path):
        _config_cache = {}
        return _config_cache

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        merged = dict(raw)
        if isinstance(raw.get("app"), dict):
            merged["app"] = dict(raw.get("app", {}))
        merged.update(merged.get("app", {}))
        _config_cache = _apply_env_overrides(merged)
    except Exception:
        _config_cache = {}
    return _config_cache


def get_app_config() -> Dict[str, Any]:
    """Public helper used throughout the codebase to obtain configuration.
    The returned dict can be safely modified by the caller if needed.
    """
    return _load_config().copy()


def get_config() -> Dict[str, Any]:
    """Legacy alias kept for backward compatibility - behaves like get_app_config."""
    return get_app_config()