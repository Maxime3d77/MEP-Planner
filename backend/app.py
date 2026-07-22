import asyncio
import hashlib
import html
import io
import json
import os
import re
import smtplib
import sqlite3
import ssl
import secrets
import time
import uuid
import shutil
import tempfile
import zipfile
import platform
from urllib.parse import quote, urlencode
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, RedirectResponse, FileResponse
from pydantic import BaseModel, EmailStr
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

APP_VERSION = "5.1.2"
app = FastAPI(title="MEP Planner API", version=APP_VERSION)
oidc_states: dict[str, dict[str, Any]] = {}
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])

REDMINE_URL = os.getenv("REDMINE_URL", "").rstrip("/")
REDMINE_API_KEY = os.getenv("REDMINE_API_KEY", "")
TAG_FIELD = os.getenv("REDMINE_TAG_FIELD", "Tag").strip()
TAG_VALUE = os.getenv("REDMINE_TAG_VALUE", "MEP").strip()
ENV_FIELD = os.getenv("REDMINE_ENV_FIELD", "Environnement").strip()
START_TIME_FIELD = os.getenv("REDMINE_START_TIME_FIELD", "Heure de début").strip()
END_TIME_FIELD = os.getenv("REDMINE_END_TIME_FIELD", "Heure de fin").strip()
ALLOW_DEMO = os.getenv("ALLOW_DEMO", "false").lower() == "true"
POLL_INTERVAL = max(60, int(os.getenv("POLL_INTERVAL_SECONDS", "300")))
MAX_REDMINE_PAGES = max(1, int(os.getenv("MAX_REDMINE_PAGES", "50")))
TIMEZONE = ZoneInfo(os.getenv("TZ", "Europe/Paris"))
DONE_STATUSES = {v.strip().casefold() for v in os.getenv("DONE_STATUSES", "Done;Closed;Terminé;Terminée;Résolu;Resolved").split(";") if v.strip()}

SMTP_ENABLED = os.getenv("SMTP_ENABLED", "false").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "MEP Planner <mep-planner@localhost>")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "false").lower() == "true"
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
SMTP_TIMEOUT = max(5, int(os.getenv("SMTP_TIMEOUT_SECONDS", "15")))
SMTP_RECIPIENTS = [v.strip() for v in os.getenv("SMTP_RECIPIENTS", "").split(";") if v.strip()]
DAILY_EMAIL_ENABLED = os.getenv("DAILY_EMAIL_ENABLED", "true").lower() == "true"
DAILY_EMAIL_HOUR = int(os.getenv("DAILY_EMAIL_HOUR", "8"))
DAILY_EMAIL_MINUTE = int(os.getenv("DAILY_EMAIL_MINUTE", "0"))

BRAND_NAME = os.getenv("BRAND_NAME", "MEP Planner").strip() or "MEP Planner"
BRAND_SUBTITLE = os.getenv("BRAND_SUBTITLE", "Pilotage des mises en production").strip()
BRAND_ACCENT = os.getenv("BRAND_ACCENT", "#5B7CFA").strip() or "#5B7CFA"
BRAND_LOGO_PATH = Path(os.getenv("BRAND_LOGO_PATH", "/app/branding/logo.png"))
COMPANY_NAME_DEFAULT = os.getenv("COMPANY_NAME", "My Company").strip()
COMPANY_SUBTITLE_DEFAULT = os.getenv("COMPANY_SUBTITLE", "IT Operations").strip()
COMPANY_ACCENT_DEFAULT = os.getenv("COMPANY_ACCENT", "").strip()
COMPANY_CONTACT_EMAIL_DEFAULT = os.getenv("COMPANY_CONTACT_EMAIL", "").strip()
COMPANY_FOOTER_DEFAULT = os.getenv("COMPANY_FOOTER", "").strip()
APP_LANGUAGE_DEFAULT = os.getenv("APP_LANGUAGE", "fr").strip().lower() if os.getenv("APP_LANGUAGE", "fr").strip().lower() in {"fr","en"} else "fr"
COMMUNICATION_LANGUAGE_DEFAULT = os.getenv("COMMUNICATION_LANGUAGE", APP_LANGUAGE_DEFAULT).strip().lower() if os.getenv("COMMUNICATION_LANGUAGE", APP_LANGUAGE_DEFAULT).strip().lower() in {"fr","en"} else APP_LANGUAGE_DEFAULT
APP_PUBLIC_URL_DEFAULT = os.getenv("APP_PUBLIC_URL", "").strip().rstrip("/")
MATRIX_ENABLED_DEFAULT = os.getenv("MATRIX_ENABLED", "false").lower() == "true"
MATRIX_HOMESERVER_DEFAULT = os.getenv("MATRIX_HOMESERVER", "").strip().rstrip("/")
MATRIX_ACCESS_TOKEN_DEFAULT = os.getenv("MATRIX_ACCESS_TOKEN", "").strip()
MATRIX_ROOM_ID_DEFAULT = os.getenv("MATRIX_ROOM_ID", "").strip()
MATRIX_NOTIFY_NEW_DEFAULT = os.getenv("MATRIX_NOTIFY_NEW", "true").lower() == "true"
MATRIX_NOTIFY_CHANGED_DEFAULT = os.getenv("MATRIX_NOTIFY_CHANGED", "true").lower() == "true"
MATRIX_NOTIFY_DAILY_DEFAULT = os.getenv("MATRIX_NOTIFY_DAILY", "false").lower() == "true"

# LDAP defaults. Values saved from the administration interface override these defaults.
LDAP_ENABLED_DEFAULT = os.getenv("LDAP_ENABLED", "false").lower() == "true"
LDAP_NAME_DEFAULT = os.getenv("LDAP_NAME", "Enterprise directory").strip()
LDAP_DIRECTORY_TYPE_DEFAULT = os.getenv("LDAP_DIRECTORY_TYPE", "openldap").strip().lower()
LDAP_URL_DEFAULT = os.getenv("LDAP_URL", "").strip()
LDAP_PORT_DEFAULT = int(os.getenv("LDAP_PORT", "636"))
LDAP_BIND_DN_DEFAULT = os.getenv("LDAP_BIND_DN", "").strip()
LDAP_BIND_PASSWORD_DEFAULT = os.getenv("LDAP_BIND_PASSWORD", "")
LDAP_BASE_DN_DEFAULT = os.getenv("LDAP_USER_BASE_DN", os.getenv("LDAP_BASE_DN", "")).strip()
LDAP_USER_FILTER_DEFAULT = os.getenv("LDAP_USER_FILTER", "(&(objectClass=person)(uid={username}))").strip()
LDAP_LOGIN_ATTRIBUTE_DEFAULT = os.getenv("LDAP_USER_LOGIN_ATTRIBUTE", "uid").strip()
LDAP_NAME_ATTRIBUTE_DEFAULT = os.getenv("LDAP_USER_FIRSTNAME_ATTRIBUTE", "givenName").strip()
LDAP_LAST_NAME_ATTRIBUTE_DEFAULT = os.getenv("LDAP_USER_LASTNAME_ATTRIBUTE", "sn").strip()
LDAP_EMAIL_ATTRIBUTE_DEFAULT = os.getenv("LDAP_USER_EMAIL_ATTRIBUTE", "mail").strip()
LDAP_GROUP_BASE_DN_DEFAULT = os.getenv("LDAP_GROUP_BASE_DN", "").strip()
LDAP_GROUP_OBJECT_CLASS_DEFAULT = os.getenv("LDAP_GROUP_OBJECT_CLASS", "posixGroup").strip()
LDAP_GROUP_NAME_ATTRIBUTE_DEFAULT = os.getenv("LDAP_GROUP_NAME_ATTRIBUTE", "cn").strip()
LDAP_GROUP_MEMBER_ATTRIBUTE_DEFAULT = os.getenv("LDAP_GROUP_MEMBER_ATTRIBUTE", "memberUid").strip()
LDAP_REFERENCE_ATTRIBUTE_DEFAULT = os.getenv("LDAP_GROUP_REFERENCE_ATTRIBUTE", "uid").strip()
LDAP_GROUP_FILTER_DEFAULT = os.getenv("LDAP_GROUP_FILTER", "({member_attribute}={reference})").strip()
LDAP_GROUP_MAP_DEFAULT = os.getenv("LDAP_GROUP_MAP", "").strip()
LDAP_VERIFY_TLS_DEFAULT = os.getenv("LDAP_VERIFY_TLS", "true").lower() == "true"
LDAP_JIT_DEFAULT = os.getenv("LDAP_JIT_PROVISIONING", "true").lower() == "true"

DATA_DIR = Path("/app/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = DATA_DIR / "mep_planner.sqlite3"
STATE_FILE = DATA_DIR / "issues_state.json"
BRANDING_DIR = DATA_DIR / "branding"
BRANDING_DIR.mkdir(parents=True, exist_ok=True)
COMPANY_LOGO_FILE = BRANDING_DIR / "company-logo.png"
COMPANY_LOGO_DARK_FILE = BRANDING_DIR / "company-logo-dark.png"
COMPANY_FAVICON_FILE = BRANDING_DIR / "favicon.png"
LOGIN_BACKGROUND_FILE = BRANDING_DIR / "login-background.webp"
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "/app/backups"))
LOG_DIR = Path(os.getenv("LOG_DIR", "/app/logs"))
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
LDAP_CA_FILE = DATA_DIR / "certificates" / "ldap-ca.pem"
LDAP_CA_FILE.parent.mkdir(parents=True, exist_ok=True)

cache: dict[str, Any] = {"mode":"loading","issues":[],"last_sync":None,"last_attempt":None,"error":None,"pages_read":0,"tickets_read":0}
sync_lock = asyncio.Lock()

class ResendRequest(BaseModel):
    recipients: list[EmailStr] | None = None
    include_pdf: bool = True
    include_calendar: bool = True
    note: str = ""

class BrandingSettings(BaseModel):
    company_name: str = ""
    company_subtitle: str = ""
    company_accent: str = ""
    company_contact_email: str = ""
    company_footer: str = ""
    language: str = "fr"
    communication_language: str = "fr"
    app_public_url: str = ""
    matrix_enabled: bool = False
    matrix_homeserver: str = ""
    matrix_access_token: str = ""
    matrix_room_id: str = ""
    matrix_notify_new: bool = True
    matrix_notify_changed: bool = True
    matrix_notify_daily: bool = False

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
ADMIN_SESSION_HOURS = max(1, int(os.getenv("ADMIN_SESSION_HOURS", "8")))
GITHUB_REPOSITORY_URL = os.getenv("GITHUB_REPOSITORY_URL", "https://github.com/Maxime3d77/MEP-Planner").rstrip("/")
GITHUB_API_REPOSITORY = os.getenv("GITHUB_API_REPOSITORY", "Maxime3d77/MEP-Planner").strip()
GITHUB_CHECK_TIMEOUT_SECONDS = max(3, int(os.getenv("GITHUB_CHECK_TIMEOUT_SECONDS", "8")))
admin_sessions: dict[str, float] = {}

class BackupCreateRequest(BaseModel):
    name: str = ""
    include_logs: bool = False

class RestoreRequest(BaseModel):
    backup_name: str
    restore_database: bool = True
    restore_branding: bool = True
    restore_settings: bool = True
    restore_logs: bool = False

class AdminLoginRequest(BaseModel):
    password: str


class LocalLoginRequest(BaseModel):
    username: str
    password: str

class UserCreateRequest(BaseModel):
    username: str
    display_name: str = ""
    email: str = ""
    password: str
    role: str = "user"
    language: str = "fr"
    communication_language: str = "fr"
    email_enabled: bool = True

class UserUpdateRequest(BaseModel):
    display_name: str = ""
    email: str = ""
    role: str = "user"
    language: str = "fr"
    communication_language: str = "fr"
    email_enabled: bool = True
    active: bool = True
    password: str = ""

class ProfileUpdateRequest(BaseModel):
    language: str = "fr"
    communication_language: str = "fr"
    email_enabled: bool = True
    password: str = ""

class InfrastructureSettings(BaseModel):
    redmine_url: str = ""
    redmine_api_key: str = ""
    redmine_tag_field: str = "Tag"
    redmine_tag_value: str = "MEP"
    redmine_env_field: str = "Environnement"
    redmine_start_time_field: str = "Heure de début"
    redmine_end_time_field: str = "Heure de fin"
    redmine_verify_tls: bool = True
    redmine_timeout_seconds: int = 20
    poll_interval_seconds: int = 300
    max_redmine_pages: int = 50
    smtp_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 25
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_recipients: str = ""
    smtp_security: str = "none"
    smtp_timeout_seconds: int = 15
    email_attach_pdf: bool = True
    email_attach_calendar: bool = True
    email_include_redmine_link: bool = True
    email_include_planner_link: bool = True
    ldap_enabled: bool = False
    ldap_name: str = ""
    ldap_directory_type: str = "openldap"
    ldap_url: str = ""
    ldap_port: int = 636
    ldap_bind_dn: str = ""
    ldap_bind_password: str = ""
    ldap_base_dn: str = ""
    ldap_user_filter: str = "(&(objectClass=person)(uid={username}))"
    ldap_login_attribute: str = "uid"
    ldap_name_attribute: str = "givenName"
    ldap_last_name_attribute: str = "sn"
    ldap_email_attribute: str = "mail"
    ldap_group_base_dn: str = ""
    ldap_group_object_class: str = "groupOfNames"
    ldap_group_name_attribute: str = "cn"
    ldap_group_member_attribute: str = "member"
    ldap_reference_attribute: str = "dn"
    ldap_group_filter: str = "({member_attribute}={reference})"
    ldap_group_map: str = ""
    ldap_verify_tls: bool = True
    ldap_jit_provisioning: bool = True
    oidc_enabled: bool = False
    oidc_discovery_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_scopes: str = "openid profile email"
    oidc_username_claim: str = "preferred_username"
    oidc_email_claim: str = "email"
    oidc_groups_claim: str = "groups"
    oidc_allowed_group: str = ""
    oidc_admin_group: str = ""
    oidc_auto_create_users: bool = True

class LdapSearchRequest(BaseModel):
    query: str = ""
    group_dn: str = ""

class LdapImportRequest(BaseModel):
    entries: list[dict[str, Any]]
    role: str = "user"

def create_admin_session() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    expires = time.time() + ADMIN_SESSION_HOURS * 3600
    admin_sessions[token] = expires
    return token, datetime.fromtimestamp(expires, TIMEZONE).isoformat(timespec="seconds")

def require_admin(authorization: str | None) -> None:
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=503, detail="ADMIN_PASSWORD is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Administrator authentication required")
    token = authorization[7:].strip()
    expires = admin_sessions.get(token, 0)
    if expires <= time.time():
        admin_sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Administrator session expired")


user_sessions: dict[str, dict[str, Any]] = {}

def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240000)
    return f"pbkdf2_sha256$240000${salt.hex()}${digest.hex()}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, rounds, salt_hex, digest_hex = encoded.split("$", 3)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)).hex()
        return secrets.compare_digest(candidate, digest_hex)
    except Exception:
        return False

def create_user_session(user: dict[str, Any]) -> tuple[str, str]:
    token = secrets.token_urlsafe(40)
    expires = time.time() + ADMIN_SESSION_HOURS * 3600
    user_sessions[token] = {"user_id": user["id"], "role": user["role"], "expires": expires}
    return token, datetime.fromtimestamp(expires, TIMEZONE).isoformat(timespec="seconds")

def current_user(authorization: str | None, required: bool = True) -> dict[str, Any] | None:
    if not authorization or not authorization.startswith("Bearer "):
        if required: raise HTTPException(401, "Authentication required")
        return None
    token = authorization[7:].strip()
    session = user_sessions.get(token)
    if not session or session["expires"] <= time.time():
        user_sessions.pop(token, None)
        if required: raise HTTPException(401, "Session expired")
        return None
    with db() as con:
        row = con.execute("SELECT * FROM users WHERE id=? AND active=1", (session["user_id"],)).fetchone()
    if not row:
        if required: raise HTTPException(401, "User disabled")
        return None
    return dict(row)

def require_admin_or_user_admin(authorization: str | None) -> dict[str, Any] | None:
    try:
        require_admin(authorization)
        return None
    except HTTPException:
        user = current_user(authorization)
        if user.get("role") != "admin": raise HTTPException(403, "Administrator role required")
        return user

def bool_setting(key: str, default: bool) -> bool:
    return get_setting(key, str(default)).lower() == "true"

def int_setting(key: str, default: int) -> int:
    """Read an integer setting safely, falling back when the stored value is invalid."""
    try:
        return int(str(get_setting(key, str(default))).strip())
    except (TypeError, ValueError):
        return int(default)

def runtime_config() -> dict[str, Any]:
    security_default = "ssl" if SMTP_USE_SSL else ("starttls" if SMTP_USE_TLS else "none")
    return {
        "redmine_url": get_setting("redmine_url", REDMINE_URL).rstrip("/"),
        "redmine_api_key": get_setting("redmine_api_key", REDMINE_API_KEY),
        "redmine_tag_field": get_setting("redmine_tag_field", TAG_FIELD),
        "redmine_tag_value": get_setting("redmine_tag_value", TAG_VALUE),
        "redmine_env_field": get_setting("redmine_env_field", ENV_FIELD),
        "redmine_start_time_field": get_setting("redmine_start_time_field", START_TIME_FIELD),
        "redmine_end_time_field": get_setting("redmine_end_time_field", END_TIME_FIELD),
        "redmine_verify_tls": bool_setting("redmine_verify_tls", True),
        "redmine_timeout_seconds": int(get_setting("redmine_timeout_seconds", "20")),
        "poll_interval_seconds": int(get_setting("poll_interval_seconds", str(POLL_INTERVAL))),
        "max_redmine_pages": int(get_setting("max_redmine_pages", str(MAX_REDMINE_PAGES))),
        "smtp_enabled": bool_setting("smtp_enabled", SMTP_ENABLED),
        "smtp_host": get_setting("smtp_host", SMTP_HOST),
        "smtp_port": int(get_setting("smtp_port", str(SMTP_PORT))),
        "smtp_username": get_setting("smtp_username", SMTP_USERNAME),
        "smtp_password": get_setting("smtp_password", SMTP_PASSWORD),
        "smtp_from": get_setting("smtp_from", SMTP_FROM),
        "smtp_recipients": get_setting("smtp_recipients", ";".join(SMTP_RECIPIENTS)),
        "smtp_security": get_setting("smtp_security", security_default),
        "smtp_timeout_seconds": int(get_setting("smtp_timeout_seconds", str(SMTP_TIMEOUT))),
        "email_attach_pdf": bool_setting("email_attach_pdf", True),
        "email_attach_calendar": bool_setting("email_attach_calendar", True),
        "email_include_redmine_link": bool_setting("email_include_redmine_link", True),
        "email_include_planner_link": bool_setting("email_include_planner_link", True),
        "ldap_enabled": bool_setting("ldap_enabled", LDAP_ENABLED_DEFAULT),
        "ldap_name": get_setting("ldap_name", LDAP_NAME_DEFAULT),
        "ldap_directory_type": get_setting("ldap_directory_type", LDAP_DIRECTORY_TYPE_DEFAULT),
        "ldap_url": get_setting("ldap_url", LDAP_URL_DEFAULT),
        "ldap_port": int_setting("ldap_port", LDAP_PORT_DEFAULT),
        "ldap_bind_dn": get_setting("ldap_bind_dn", LDAP_BIND_DN_DEFAULT),
        "ldap_bind_password": get_setting("ldap_bind_password", LDAP_BIND_PASSWORD_DEFAULT),
        "ldap_base_dn": get_setting("ldap_base_dn", LDAP_BASE_DN_DEFAULT),
        "ldap_user_filter": get_setting("ldap_user_filter", LDAP_USER_FILTER_DEFAULT),
        "ldap_login_attribute": get_setting("ldap_login_attribute", LDAP_LOGIN_ATTRIBUTE_DEFAULT),
        "ldap_name_attribute": get_setting("ldap_name_attribute", LDAP_NAME_ATTRIBUTE_DEFAULT),
        "ldap_last_name_attribute": get_setting("ldap_last_name_attribute", LDAP_LAST_NAME_ATTRIBUTE_DEFAULT),
        "ldap_email_attribute": get_setting("ldap_email_attribute", LDAP_EMAIL_ATTRIBUTE_DEFAULT),
        "ldap_group_base_dn": get_setting("ldap_group_base_dn", LDAP_GROUP_BASE_DN_DEFAULT),
        "ldap_group_object_class": get_setting("ldap_group_object_class", LDAP_GROUP_OBJECT_CLASS_DEFAULT),
        "ldap_group_name_attribute": get_setting("ldap_group_name_attribute", LDAP_GROUP_NAME_ATTRIBUTE_DEFAULT),
        "ldap_group_member_attribute": get_setting("ldap_group_member_attribute", LDAP_GROUP_MEMBER_ATTRIBUTE_DEFAULT),
        "ldap_reference_attribute": get_setting("ldap_reference_attribute", LDAP_REFERENCE_ATTRIBUTE_DEFAULT),
        "ldap_group_filter": get_setting("ldap_group_filter", LDAP_GROUP_FILTER_DEFAULT),
        "ldap_group_map": get_setting("ldap_group_map", LDAP_GROUP_MAP_DEFAULT),
        "ldap_verify_tls": bool_setting("ldap_verify_tls", LDAP_VERIFY_TLS_DEFAULT),
        "ldap_jit_provisioning": bool_setting("ldap_jit_provisioning", LDAP_JIT_DEFAULT),
        "ldap_ca_configured": LDAP_CA_FILE.exists(),
        "oidc_enabled": bool_setting("oidc_enabled", False),
        "oidc_discovery_url": get_setting("oidc_discovery_url", ""),
        "oidc_client_id": get_setting("oidc_client_id", ""),
        "oidc_client_secret": get_setting("oidc_client_secret", ""),
        "oidc_scopes": get_setting("oidc_scopes", "openid profile email"),
        "oidc_username_claim": get_setting("oidc_username_claim", "preferred_username"),
        "oidc_email_claim": get_setting("oidc_email_claim", "email"),
        "oidc_groups_claim": get_setting("oidc_groups_claim", "groups"),
        "oidc_allowed_group": get_setting("oidc_allowed_group", ""),
        "oidc_admin_group": get_setting("oidc_admin_group", ""),
        "oidc_auto_create_users": bool_setting("oidc_auto_create_users", True),
    }

def public_runtime_config() -> dict[str, Any]:
    cfg = runtime_config().copy()
    for secret in ("redmine_api_key","smtp_password","ldap_bind_password","oidc_client_secret"):
        cfg[secret + "_configured"] = bool(cfg.get(secret))
        cfg[secret] = ""
    cfg["oidc_redirect_uri"] = (app_public_url() or "http://localhost:8080") + "/api/auth/oidc/callback"
    return cfg

def serialize_user(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    d = dict(row)
    d.pop("password_hash", None)
    d["email_enabled"] = bool(d.get("email_enabled", 1)); d["active"] = bool(d.get("active", 1))
    return d

def version_tuple(value: str) -> tuple[int, ...]:
    match = re.search(r"(\d+(?:\.\d+)+)", value or "")
    return tuple(int(v) for v in match.group(1).split(".")) if match else (0,)

async def github_version_status() -> dict[str, Any]:
    result = {"current_version": APP_VERSION, "latest_version": None, "update_available": False, "repository_url": GITHUB_REPOSITORY_URL, "release_url": None, "status": "unknown", "error": None}
    if not GITHUB_API_REPOSITORY:
        result.update(status="disabled", error="GitHub repository is not configured")
        return result
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"MEP-Planner/{APP_VERSION}"}
    try:
        async with httpx.AsyncClient(timeout=GITHUB_CHECK_TIMEOUT_SECONDS, follow_redirects=True) as client:
            release = await client.get(f"https://api.github.com/repos/{GITHUB_API_REPOSITORY}/releases/latest", headers=headers)
            if release.status_code == 200:
                data = release.json(); tag = str(data.get("tag_name", ""))
                result.update(latest_version=tag.lstrip("vV"), release_url=data.get("html_url"), status="ok")
            elif release.status_code == 404:
                tags = await client.get(f"https://api.github.com/repos/{GITHUB_API_REPOSITORY}/tags?per_page=1", headers=headers)
                tags.raise_for_status(); items = tags.json()
                if items:
                    tag = str(items[0].get("name", "")); result.update(latest_version=tag.lstrip("vV"), release_url=f"{GITHUB_REPOSITORY_URL}/releases", status="tag")
                else:
                    result.update(status="no_release")
            else:
                release.raise_for_status()
        if result["latest_version"]:
            result["update_available"] = version_tuple(result["latest_version"]) > version_tuple(APP_VERSION)
        return result
    except Exception as exc:
        result.update(status="error", error=str(exc))
        return result


def now_local() -> datetime: return datetime.now(TIMEZONE)

def brand_logo_bytes() -> bytes | None:
    try:return BRAND_LOGO_PATH.read_bytes() if BRAND_LOGO_PATH.is_file() else None
    except OSError:return None

def company_logo_bytes() -> bytes | None:
    try:
        return COMPANY_LOGO_FILE.read_bytes() if COMPANY_LOGO_FILE.is_file() else None
    except OSError:
        return None

def get_setting(key: str, default: str = "") -> str:
    try:
        with db() as con:
            row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return str(row["value"]) if row else default
    except sqlite3.Error:
        return default

def set_setting(key: str, value: str) -> None:
    with db() as con:
        con.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

def branding_settings() -> dict[str, Any]:
    return {
        "brand_name": BRAND_NAME,
        "brand_subtitle": BRAND_SUBTITLE,
        "brand_accent": safe_accent(),
        "company_name": get_setting("company_name", COMPANY_NAME_DEFAULT),
        "company_subtitle": get_setting("company_subtitle", COMPANY_SUBTITLE_DEFAULT),
        "company_accent": get_setting("company_accent", COMPANY_ACCENT_DEFAULT),
        "company_contact_email": get_setting("company_contact_email", COMPANY_CONTACT_EMAIL_DEFAULT),
        "company_footer": get_setting("company_footer", COMPANY_FOOTER_DEFAULT),
        "company_logo_configured": COMPANY_LOGO_FILE.is_file(),
        "company_logo_dark_configured": COMPANY_LOGO_DARK_FILE.is_file(),
        "company_favicon_configured": COMPANY_FAVICON_FILE.is_file(),
        "login_background_configured": LOGIN_BACKGROUND_FILE.is_file(),
        "language": get_setting("language", APP_LANGUAGE_DEFAULT),
        "communication_language": get_setting("communication_language", COMMUNICATION_LANGUAGE_DEFAULT),
        "app_public_url": get_setting("app_public_url", APP_PUBLIC_URL_DEFAULT),
        "matrix_enabled": get_setting("matrix_enabled", str(MATRIX_ENABLED_DEFAULT)).lower() == "true",
        "matrix_homeserver": get_setting("matrix_homeserver", MATRIX_HOMESERVER_DEFAULT),
        "matrix_room_id": get_setting("matrix_room_id", MATRIX_ROOM_ID_DEFAULT),
        "matrix_token_configured": bool(get_setting("matrix_access_token", MATRIX_ACCESS_TOKEN_DEFAULT)),
        "matrix_notify_new": get_setting("matrix_notify_new", str(MATRIX_NOTIFY_NEW_DEFAULT)).lower() == "true",
        "matrix_notify_changed": get_setting("matrix_notify_changed", str(MATRIX_NOTIFY_CHANGED_DEFAULT)).lower() == "true",
        "matrix_notify_daily": get_setting("matrix_notify_daily", str(MATRIX_NOTIFY_DAILY_DEFAULT)).lower() == "true",
    }

def safe_accent() -> str:
    value=BRAND_ACCENT.strip()
    return value if re.fullmatch(r"#[0-9A-Fa-f]{6}",value) else "#5B7CFA"

def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_FILE, timeout=20)
    connection.row_factory = sqlite3.Row
    return connection

def init_db() -> None:
    with db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS settings (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notifications (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          issue_id INTEGER,
          issue_version TEXT NOT NULL,
          notification_type TEXT NOT NULL,
          subject TEXT NOT NULL,
          recipients TEXT NOT NULL,
          recipient_key TEXT NOT NULL,
          sent_at TEXT NOT NULL,
          status TEXT NOT NULL,
          error TEXT,
          message_id TEXT,
          manual INTEGER NOT NULL DEFAULT 0,
          pdf_attached INTEGER NOT NULL DEFAULT 0
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_auto_notification
          ON notifications(issue_id, issue_version, notification_type, recipient_key)
          WHERE manual = 0 AND status = 'sent';
        CREATE INDEX IF NOT EXISTS idx_notification_issue ON notifications(issue_id, sent_at DESC);
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL UNIQUE COLLATE NOCASE,
          display_name TEXT NOT NULL DEFAULT '',
          email TEXT NOT NULL DEFAULT '',
          password_hash TEXT NOT NULL DEFAULT '',
          source TEXT NOT NULL DEFAULT 'local',
          external_id TEXT NOT NULL DEFAULT '',
          role TEXT NOT NULL DEFAULT 'user',
          language TEXT NOT NULL DEFAULT 'fr',
          communication_language TEXT NOT NULL DEFAULT 'fr',
          email_enabled INTEGER NOT NULL DEFAULT 1,
          active INTEGER NOT NULL DEFAULT 1,
          last_login TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          occurred_at TEXT NOT NULL,
          actor TEXT NOT NULL,
          action TEXT NOT NULL,
          details TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS system_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          occurred_at TEXT NOT NULL,
          system TEXT NOT NULL,
          level TEXT NOT NULL,
          message TEXT NOT NULL,
          details TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_system_logs_type_date ON system_logs(system, occurred_at DESC);
        ''')
        count = con.execute('SELECT COUNT(*) AS c FROM users').fetchone()['c']
        if count == 0 and ADMIN_PASSWORD:
            now = now_local().isoformat(timespec='seconds')
            con.execute('INSERT INTO users(username,display_name,email,password_hash,source,role,language,communication_language,email_enabled,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', ('admin','Administrator','',hash_password(ADMIN_PASSWORD),'local','admin',APP_LANGUAGE_DEFAULT,COMMUNICATION_LANGUAGE_DEFAULT,1,1,now,now))

def log_event(system: str, level: str, message: str, details: str = '') -> None:
    try:
        with db() as con:
            con.execute('INSERT INTO system_logs(occurred_at,system,level,message,details) VALUES(?,?,?,?,?)',
                        (now_local().isoformat(timespec='seconds'), system.lower(), level.lower(), str(message), str(details or '')))
    except Exception as exc:
        print(f'Unable to persist {system} log: {exc}', flush=True)

def load_json(path: Path, default: Any) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return default

def save_json(path: Path, value: Any) -> None:
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8'); tmp.replace(path)

def custom_field_map(issue: dict[str, Any]) -> dict[str,str]:
    result={}
    for field in issue.get('custom_fields',[]):
        value=field.get('value','')
        if isinstance(value,list): value=', '.join(map(str,value))
        result[str(field.get('name','')).strip()]=str(value).strip()
    return result

def normalize_time(value: str) -> str | None:
    value=(value or '').strip()
    if not value:return None
    try:
        parts=value.replace('h',':').split(':')
        if len(parts) > 2: return None
        hour=int(parts[0]); minute=int(parts[1]) if len(parts)>1 else 0
        if not (0 <= hour <= 23 and 0 <= minute <= 59): return None
        return f"{hour:02d}:{minute:02d}"
    except (ValueError, TypeError):return None

def normalize_issue(raw: dict[str,Any], cfg: dict[str,Any]) -> dict[str,Any]:
    f=custom_field_map(raw)
    tags=[x.strip() for x in f.get(cfg['redmine_tag_field'],'').replace(';',',').split(',') if x.strip()]
    start=raw.get('start_date') or str(raw.get('created_on',''))[:10]; due=raw.get('due_date') or start
    estimated=raw.get('estimated_hours') or 0
    try: estimated=float(estimated)
    except (TypeError,ValueError): estimated=0
    start_time=normalize_time(f.get(cfg['redmine_start_time_field'],''))
    end_time=normalize_time(f.get(cfg['redmine_end_time_field'],''))
    if start_time and not end_time and estimated:
        end_time=(datetime.strptime(start_time,'%H:%M')+timedelta(hours=estimated)).strftime('%H:%M')
    return {'id':raw.get('id'),'subject':raw.get('subject',''),'status':raw.get('status',{}).get('name','—'),'priority':raw.get('priority',{}).get('name','—'),'author':raw.get('author',{}).get('name','—'),'assigned_to':raw.get('assigned_to',{}).get('name','Non assigné'),'start_date':start,'due_date':due,'start_time':start_time,'end_time':end_time,'has_time':bool(start_time),'estimated_hours':estimated,'environment':f.get(cfg['redmine_env_field'],'Non défini') or 'Non défini','description':raw.get('description') or 'Aucune description.','tags':tags,'url':f"{cfg['redmine_url'].rstrip('/')}/issues/{raw.get('id')}",'updated_on':raw.get('updated_on','')}

def demo_issues() -> list[dict[str,Any]]:
    today=now_local().date().isoformat()
    return [{'id':1258,'subject':'Déploiement correctif - Authentification','status':'To Do','priority':'Immédiat','author':'Julien Martin','assigned_to':'Sophie Dubois','start_date':today,'due_date':today,'start_time':'09:00','end_time':'10:30','has_time':True,'estimated_hours':1.5,'environment':'Production','description':'Correctif d’authentification avec validation et procédure de rollback.','tags':['MEP'],'url':'#','updated_on':now_local().isoformat()}]

def is_mep(i: dict[str,Any], cfg: dict[str,Any]) -> bool:
    expected=str(cfg.get('redmine_tag_value','MEP')).strip().casefold()
    return any(t.casefold()==expected or 'mep urgente' in t.casefold() for t in i.get('tags',[]))
def is_done(i): return str(i.get('status','')).strip().casefold() in DONE_STATUSES

def priority_level(issue: dict[str,Any]) -> int:
    p=str(issue.get('priority','')).strip().casefold()
    if 'immédiat' in p or 'immediat' in p:return 4
    if 'urgent' in p:return 3
    if 'haut' in p or 'high' in p:return 2
    return 1

def issue_signature(issue: dict[str,Any]) -> dict[str,Any]:
    return {k:issue.get(k) for k in ('subject','status','priority','assigned_to','start_date','due_date','start_time','end_time','environment','estimated_hours','updated_on')}

def issue_version(issue: dict[str,Any]) -> str:
    payload=json.dumps(issue_signature(issue),sort_keys=True,ensure_ascii=False).encode(); return hashlib.sha256(payload).hexdigest()[:24]

def recipient_key(recipients:list[str])->str: return hashlib.sha256(';'.join(sorted(x.casefold() for x in recipients)).encode()).hexdigest()[:24]

async def fetch_redmine():
    cfg = runtime_config()
    redmine_url = cfg['redmine_url'].rstrip('/')
    redmine_key = cfg['redmine_api_key']
    if not redmine_url or not redmine_key or redmine_key=='change_me':
        if ALLOW_DEMO:return 'demo',demo_issues(),1,1
        raise RuntimeError('Configuration Redmine manquante')
    all_issues=[];seen=set();offset=0;pages=0
    timeout=httpx.Timeout(connect=10,read=cfg['redmine_timeout_seconds'],write=10,pool=10)
    async with httpx.AsyncClient(timeout=timeout,verify=cfg['redmine_verify_tls']) as client:
        for idx in range(cfg["max_redmine_pages"]):
            pages=idx+1; print(f'Redmine page {pages}, offset {offset}',flush=True)
            r=await client.get(f'{redmine_url}/issues.json',params={'limit':100,'offset':offset,'status_id':'*','sort':'updated_on:desc'},headers={'X-Redmine-API-Key':redmine_key});r.raise_for_status();p=r.json();batch=p.get('issues',[])
            if not batch:break
            added=0
            for raw in batch:
                if isinstance(raw.get('id'),int) and raw['id'] not in seen:seen.add(raw['id']);all_issues.append(raw);added+=1
            if not added:break
            offset+=len(batch)
            if offset>=int(p.get('total_count',offset)):break
    normalized=[normalize_issue(raw,cfg) for raw in all_issues]
    selected=[i for i in normalized if is_mep(i,cfg)]
    print(f'Synchronisation terminée : {len(all_issues)} tickets lus, {len(selected)} MEP retenues.',flush=True)
    return 'redmine',selected,pages,len(all_issues)

def communication_language() -> str:
    value=get_setting("communication_language",COMMUNICATION_LANGUAGE_DEFAULT).strip().lower()
    return value if value in {"fr","en"} else "fr"

def tr(fr:str,en:str,lang:str|None=None)->str:
    return en if (lang or communication_language())=="en" else fr

def planning_label(issue: dict[str,Any], lang: str|None=None) -> str:
    if not issue.get("start_time"):
        return f"{issue.get('start_date','—')} · {tr('heure à préciser','time to be confirmed',lang)}"
    ending=f" - {issue.get('end_time')}" if issue.get('end_time') else ""
    return f"{issue.get('start_date','—')} · {issue.get('start_time')}{ending}"

def report_pdf(issue: dict[str,Any], communication: str|None=None, lang: str|None=None) -> bytes:
    lang=lang or communication_language()
    communication=communication or tr('Fiche de communication MEP','Release communication sheet',lang)
    accent = colors.HexColor(safe_accent())
    navy = colors.HexColor('#0B1730'); ink = colors.HexColor('#18243A'); muted = colors.HexColor('#69758C')
    pale = colors.HexColor('#F3F6FC'); line = colors.HexColor('#DCE3F0'); success = colors.HexColor('#187A55')
    priority_color = {4: colors.HexColor('#B20F3B'), 3: colors.HexColor('#D7334B'), 2: colors.HexColor('#C67A11')}.get(priority_level(issue), accent)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=14*mm, bottomMargin=15*mm,
        title=f"MEP #{issue['id']} - {issue['subject']}", author=BRAND_NAME, subject=communication)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BrandEyebrow', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=accent, spaceAfter=2, letterSpacing=1.4))
    styles.add(ParagraphStyle(name='PdfTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=navy, alignment=TA_LEFT, spaceAfter=3))
    styles.add(ParagraphStyle(name='PdfSubtitle', parent=styles['BodyText'], fontSize=9.5, leading=13, textColor=muted))
    styles.add(ParagraphStyle(name='IssueTitle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=17, leading=21, textColor=ink, spaceAfter=2))
    styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=navy, spaceBefore=3, spaceAfter=6))
    styles.add(ParagraphStyle(name='BodyModern', parent=styles['BodyText'], fontSize=9.5, leading=14, textColor=ink))
    styles.add(ParagraphStyle(name='SmallMuted', parent=styles['BodyText'], fontSize=7.8, leading=11, textColor=muted))
    styles.add(ParagraphStyle(name='Footer', parent=styles['BodyText'], fontSize=7.5, leading=10, alignment=TA_CENTER, textColor=muted))
    settings=branding_settings()
    logo_data = brand_logo_bytes()
    company_data = company_logo_bytes()
    logo = Image(io.BytesIO(logo_data), width=16*mm, height=16*mm) if logo_data else ''
    company_logo = Image(io.BytesIO(company_data), width=20*mm, height=16*mm) if company_data else ''
    brand_copy = [Paragraph(html.escape(BRAND_NAME.upper()), styles['BrandEyebrow']), Paragraph(html.escape(communication), styles['PdfTitle']), Paragraph(html.escape(BRAND_SUBTITLE), styles['PdfSubtitle'])]
    company_copy = []
    header = Table([[logo, brand_copy, company_logo, company_copy]], colWidths=[20*mm,132*mm,22*mm,0*mm], hAlign='LEFT')
    header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    pill_style = ParagraphStyle('PriorityPill', parent=styles['BodyText'], alignment=TA_CENTER, fontSize=9, leading=12, textColor=colors.white)
    issue_header = Table([[[Paragraph(f"Ticket #{issue['id']}", styles['BrandEyebrow']), Paragraph(html.escape(issue['subject']), styles['IssueTitle']), Paragraph(f"{html.escape(issue['environment'])} · {html.escape(planning_label(issue,lang))}", styles['PdfSubtitle'])], Paragraph(f"<b>{html.escape(issue['priority'])}</b>", pill_style)]], colWidths=[142*mm,32*mm])
    issue_header.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),pale),('BOX',(0,0),(-1,-1),0.8,line),('LINEBEFORE',(0,0),(0,0),4,priority_color),('BACKGROUND',(1,0),(1,0),priority_color),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(0,0),12),('RIGHTPADDING',(0,0),(0,0),10),('TOPPADDING',(0,0),(-1,-1),11),('BOTTOMPADDING',(0,0),(-1,-1),11)]))
    rows=[(tr('Statut','Status',lang),issue['status'],tr('Environnement','Environment',lang),issue['environment']),(tr('Assigné à','Assigned to',lang),issue['assigned_to'],tr('Auteur','Author',lang),issue['author']),(tr('Début','Start',lang),planning_label(issue,lang),tr('Fin prévue','Expected end',lang),f"{issue['due_date']} {issue.get('end_time') or tr('heure à préciser','time to be confirmed',lang)}"),(tr('Temps estimé','Estimated time',lang),f"{issue['estimated_hours']} h",tr('Dernière mise à jour','Last update',lang),issue.get('updated_on') or '—')]
    data=[]
    for a,b,c,d in rows:
        data.append([Paragraph(f"<b>{html.escape(a)}</b><br/><font color='#69758C'>{html.escape(str(b))}</font>",styles['BodyModern']), Paragraph(f"<b>{html.escape(c)}</b><br/><font color='#69758C'>{html.escape(str(d))}</font>",styles['BodyModern'])])
    info=Table(data,colWidths=[87*mm,87*mm]); info.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.white),('BOX',(0,0),(-1,-1),0.8,line),('INNERGRID',(0,0),(-1,-1),0.5,line),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
    description=Table([[Paragraph(html.escape(issue.get('description') or tr('Aucune description.','No description provided.',lang)).replace('\n','<br/>'),styles['BodyModern'])]],colWidths=[174*mm]); description.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),pale),('BOX',(0,0),(-1,-1),0.8,line),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12)]))
    communication_text=f"<b>{tr('Communication tracée','Tracked communication',lang)}</b><br/>{tr('Cette fiche a été générée par MEP Planner. La source opérationnelle reste le ticket Redmine.','This sheet was generated by MEP Planner. The Redmine ticket remains the operational source of truth.',lang)}"
    if settings['company_footer']: communication_text += f"<br/><br/>{html.escape(settings['company_footer'])}"
    contact_text=f"<b>{tr('Généré le','Generated on',lang)}</b><br/>{now_local().strftime('%m/%d/%Y at %H:%M' if lang=='en' else '%d/%m/%Y à %H:%M')}"
    if settings['company_contact_email']: contact_text += f"<br/><br/><b>Contact</b><br/>{html.escape(settings['company_contact_email'])}"
    communication_box=Table([[Paragraph(communication_text,styles['SmallMuted']),Paragraph(contact_text,styles['SmallMuted'])]],colWidths=[125*mm,49*mm]); communication_box.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#EAF7F1')),('BOX',(0,0),(-1,-1),0.8,colors.HexColor('#B8E2CF')),('LINEBEFORE',(0,0),(0,0),4,success),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
    story=[header,Spacer(1,5*mm),HRFlowable(width='100%',thickness=2,color=accent,spaceAfter=5*mm),issue_header,Spacer(1,5*mm),Paragraph(tr('Informations de planification','Release planning information',lang),styles['SectionTitle']),info,Spacer(1,5*mm),Paragraph(tr('Description et consignes','Description and instructions',lang),styles['SectionTitle']),description,Spacer(1,5*mm),communication_box,Spacer(1,5*mm),Paragraph(f"{tr('Référence','Reference',lang)} : #{issue['id']} · {html.escape(issue['url'])}",styles['Footer'])]
    def decorate(canvas, document):
        canvas.saveState(); width,height=A4; canvas.setFillColor(accent); canvas.rect(0,height-5*mm,width,5*mm,fill=1,stroke=0); canvas.setStrokeColor(line); canvas.line(16*mm,12*mm,width-16*mm,12*mm); canvas.setFont('Helvetica',7); canvas.setFillColor(muted); canvas.drawString(16*mm,7.5*mm,BRAND_NAME); canvas.drawRightString(width-16*mm,7.5*mm,f"{tr('Page','Page',lang)} {document.page}"); canvas.restoreState()
    doc.build(story,onFirstPage=decorate,onLaterPages=decorate); return buf.getvalue()

def email_template(title:str,intro:str,issues:list[dict[str,Any]],note:str='',lang:str|None=None)->str:
    lang=lang or communication_language()
    accent=safe_accent(); cards=[]
    for i in issues:
        level=priority_level(i); card_accent={4:'#B20F3B',3:'#D7334B',2:'#C67A11'}.get(level,accent); label={4:tr('PRIORITÉ MAXIMALE','HIGHEST PRIORITY',lang),3:tr('PRIORITAIRE','PRIORITY',lang),2:tr('TRAITEMENT MOYEN','MEDIUM HANDLING',lang)}.get(level,tr('TRAITEMENT STANDARD','STANDARD HANDLING',lang))
        cards.append(f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:18px 0;background:#111B2E;border:1px solid #2A3958;border-radius:16px;overflow:hidden"><tr><td style="width:6px;background:{card_accent};font-size:0">&nbsp;</td><td style="padding:20px 22px"><div style="display:inline-block;background:{card_accent};color:#fff;border-radius:999px;padding:5px 10px;font-size:10px;font-weight:700;letter-spacing:.8px">{label}</div><div style="margin-top:12px;color:#8FA8CC;font-size:12px;font-weight:700">TICKET #{i['id']} · {html.escape(i['status']).upper()}</div><h2 style="margin:7px 0 16px;color:#FFFFFF;font-size:22px;line-height:1.25">{html.escape(i['subject'])}</h2><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="color:#D6DEEC;font-size:13px;line-height:1.6"><tr><td width="46%" style="padding:6px 0;border-bottom:1px solid #24334E"><span style="color:#7F90AA">{tr('Planification','Schedule',lang)}</span><br><strong>{html.escape(planning_label(i,lang))}</strong></td><td style="padding:6px 0;border-bottom:1px solid #24334E"><span style="color:#7F90AA">{tr('Environnement','Environment',lang)}</span><br><strong>{html.escape(i['environment'])}</strong></td></tr><tr><td style="padding:8px 0"><span style="color:#7F90AA">{tr('Assigné à','Assigned to',lang)}</span><br><strong>{html.escape(i['assigned_to'])}</strong></td><td style="padding:8px 0"><span style="color:#7F90AA">{tr('Priorité Redmine','Redmine priority',lang)}</span><br><strong>{html.escape(i['priority'])}</strong></td></tr></table><div style="margin:14px 0 18px;padding:14px;background:#0B1424;border-radius:10px;color:#B7C2D6;font-size:13px;line-height:1.55;white-space:pre-line">{html.escape(i['description'][:1200])}</div><a href="{html.escape(i['url'])}" style="display:inline-block;background:{accent};color:#fff;text-decoration:none;padding:11px 17px;border-radius:9px;font-weight:700;font-size:13px">{tr('Ouvrir le ticket Redmine','Open Redmine ticket',lang)}</a><span style="display:inline-block;margin-left:10px;color:#7F90AA;font-size:11px">{tr('Fiche PDF jointe selon la configuration','PDF sheet attached according to configuration',lang)}</span></td></tr></table>''')
    note_html=f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0;background:#FFF5D8;border:1px solid #F1D78B;border-radius:12px"><tr><td style="padding:14px 16px;color:#5F490D;font-size:13px;line-height:1.5"><strong>{tr('Note complémentaire','Additional note',lang)}</strong><br>{html.escape(note)}</td></tr></table>''' if note else ''
    settings=branding_settings()
    logo_html='<img src="cid:mep-planner-logo" width="54" height="54" alt="" style="display:block;border:0;border-radius:12px">' if brand_logo_bytes() else f'<div style="width:54px;height:54px;border-radius:12px;background:{accent};color:#fff;font-size:24px;font-weight:bold;line-height:54px;text-align:center">M</div>'
    return f'''<!doctype html><html lang="{lang}"><body style="margin:0;padding:0;background:#070C15;font-family:Arial,Helvetica,sans-serif"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#070C15"><tr><td align="center" style="padding:28px 12px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:760px"><tr><td style="background:#13203A;border:1px solid #2B3B5D;border-radius:18px;padding:26px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td width="72">{logo_html}</td><td><div style="color:#91B5FF;font-size:11px;letter-spacing:2px;font-weight:700">{html.escape(BRAND_NAME.upper())}</div><div style="color:#8392AA;font-size:11px;margin-top:4px">{html.escape(BRAND_SUBTITLE)}</div></td><td style="padding-left:18px">{('<img src="cid:company-logo" width="72" alt="" style="display:block;max-height:48px;object-fit:contain">' if company_logo_bytes() else '')}</td><td align="right" style="color:#7F90AA;font-size:11px">{tr('Communication MEP','Release communication',lang)}<br>{now_local().strftime('%d/%m/%Y · %H:%M')}</td></tr></table><h1 style="margin:24px 0 8px;color:#FFFFFF;font-size:30px;line-height:1.15">{html.escape(title)}</h1><p style="margin:0;color:#B9C5D8;font-size:15px;line-height:1.55">{html.escape(intro)}</p></td></tr><tr><td>{note_html}{''.join(cards)}</td></tr><tr><td style="padding:8px 12px 0;text-align:center;color:#65728A;font-size:10px;line-height:1.5">Communication envoyée et historisée par {html.escape(BRAND_NAME)}.<br>{html.escape(settings['company_footer']) if settings['company_footer'] else tr('Ne répondez pas à ce message automatique sauf indication contraire.','Do not reply to this automated message unless instructed otherwise.',lang)}{('<br>Contact : ' + html.escape(settings['company_contact_email'])) if settings['company_contact_email'] else ''}{('<br><a style="color:#91B5FF" href="' + html.escape(app_public_url(), quote=True) + '">MEP Planner</a>') if app_public_url() else ''}</td></tr></table></td></tr></table></body></html>'''


def escape_ics(value: Any) -> str:
    return str(value or "").replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")

def issue_datetimes(issue: dict[str, Any]) -> tuple[datetime, datetime] | None:
    if not issue.get("start_date") or not issue.get("start_time"):
        return None
    start = datetime.strptime(f"{issue['start_date']} {issue['start_time']}", "%Y-%m-%d %H:%M").replace(tzinfo=TIMEZONE)
    end_date = issue.get("due_date") or issue.get("start_date")
    end_time = issue.get("end_time")
    if end_time:
        end = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M").replace(tzinfo=TIMEZONE)
        if end <= start:
            end += timedelta(days=1)
    elif issue.get("estimated_hours"):
        end = start + timedelta(hours=float(issue["estimated_hours"]))
    else:
        end = start + timedelta(minutes=30)
    return start, end

def calendar_invitation(issue: dict[str, Any], recipients: list[str], method: str = "REQUEST", lang: str | None = None) -> bytes | None:
    times = issue_datetimes(issue)
    if not times:
        return None
    lang = lang or communication_language()
    start, end = times
    now_utc = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    sequence = int(hashlib.sha256(issue_version(issue).encode()).hexdigest()[:8], 16)
    title = f"MEP #{issue['id']} - {issue['subject']}"
    description = "\n".join([
        f"{tr('Environnement','Environment',lang)}: {issue.get('environment','—')}",
        f"{tr('Priorité','Priority',lang)}: {issue.get('priority','—')}",
        f"{tr('Statut','Status',lang)}: {issue.get('status','—')}",
        f"{tr('Assigné à','Assigned to',lang)}: {issue.get('assigned_to','—')}",
        "", str(issue.get('description') or ''), "",
        f"Redmine: {issue.get('url','')}"
    ])
    attendee_lines = "\r\n".join(f"ATTENDEE;CN={escape_ics(address)};RSVP=TRUE:mailto:{escape_ics(address)}" for address in recipients)
    status = "CANCELLED" if method == "CANCEL" else "CONFIRMED"
    content = f"""BEGIN:VCALENDAR
PRODID:-//MEP Planner//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:{method}
BEGIN:VEVENT
UID:mep-{issue['id']}@mep-planner
SEQUENCE:{sequence}
DTSTAMP:{now_utc}
DTSTART;TZID={TIMEZONE.key}:{start.strftime('%Y%m%dT%H%M%S')}
DTEND;TZID={TIMEZONE.key}:{end.strftime('%Y%m%dT%H%M%S')}
SUMMARY:{escape_ics(title)}
LOCATION:{escape_ics(issue.get('environment',''))}
DESCRIPTION:{escape_ics(description)}
URL:{escape_ics(issue.get('url',''))}
ORGANIZER;CN=MEP Planner:mailto:{escape_ics(SMTP_FROM.split('<')[-1].rstrip('>') if '<' in SMTP_FROM else SMTP_FROM)}
{attendee_lines}
STATUS:{status}
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
"""
    return content.encode("utf-8")

def app_public_url() -> str:
    return get_setting("app_public_url", APP_PUBLIC_URL_DEFAULT).strip().rstrip("/")

def issue_app_url(issue: dict[str, Any]) -> str:
    base = app_public_url()
    return f"{base}/?issue={issue['id']}" if base else ""

def matrix_config() -> dict[str, Any]:
    return {
        "enabled": get_setting("matrix_enabled", str(MATRIX_ENABLED_DEFAULT)).lower() == "true",
        "homeserver": get_setting("matrix_homeserver", MATRIX_HOMESERVER_DEFAULT).strip().rstrip("/"),
        "access_token": get_setting("matrix_access_token", MATRIX_ACCESS_TOKEN_DEFAULT).strip(),
        "room_id": get_setting("matrix_room_id", MATRIX_ROOM_ID_DEFAULT).strip(),
        "notify_new": get_setting("matrix_notify_new", str(MATRIX_NOTIFY_NEW_DEFAULT)).lower() == "true",
        "notify_changed": get_setting("matrix_notify_changed", str(MATRIX_NOTIFY_CHANGED_DEFAULT)).lower() == "true",
        "notify_daily": get_setting("matrix_notify_daily", str(MATRIX_NOTIFY_DAILY_DEFAULT)).lower() == "true",
    }

def priority_matrix_style(issue: dict[str, Any]) -> tuple[str, str, str]:
    level = priority_level(issue)
    styles = {
        4: ("#dc2626", "🚨", "Immediate"),
        3: ("#f97316", "🔥", "Urgent"),
        2: ("#eab308", "⚠️", "High"),
        1: ("#5b7cfa", "ℹ️", "Normal"),
        0: ("#64748b", "▫️", "Low"),
    }
    return styles.get(level, styles[1])

def matrix_message(issue: dict[str, Any], kind: str, lang: str | None = None) -> tuple[str, str]:
    lang = lang or communication_language()
    color, icon, _ = priority_matrix_style(issue)
    labels = {
        "new": tr("Nouvelle MEP planifiée", "New scheduled release", lang),
        "changed": tr("MEP modifiée", "Release updated", lang),
        "daily": tr("MEP du jour", "Today's release", lang),
        "test": tr("Test Matrix réussi", "Matrix test successful", lang),
    }
    heading = labels.get(kind, labels["new"])
    schedule = issue_schedule(issue, lang)
    redmine = issue.get("url", "")
    planner = issue_app_url(issue)
    plain = f"{icon} {heading} — MEP #{issue['id']} {issue['subject']} | {schedule} | {issue.get('environment') or '-'} | {redmine}"
    rows = [
        (tr("Planification", "Schedule", lang), schedule),
        (tr("Environnement", "Environment", lang), issue.get("environment") or "—"),
        (tr("Priorité", "Priority", lang), issue.get("priority") or "—"),
        (tr("Statut", "Status", lang), issue.get("status") or "—"),
        (tr("Assigné à", "Assigned to", lang), issue.get("assigned_to") or "—"),
    ]
    rows_html = "".join(f'<tr><td style="padding:4px 14px 4px 0;color:#94a3b8">{html.escape(str(k))}</td><td style="padding:4px 0"><b>{html.escape(str(v))}</b></td></tr>' for k,v in rows)
    links = f'🔗 <a href="{html.escape(redmine, quote=True)}">Redmine #{issue["id"]}</a>'
    if planner:
        links += f' &nbsp;·&nbsp; 🗓️ <a href="{html.escape(planner, quote=True)}">MEP Planner</a>'
    formatted = f'''<div style="border-left:5px solid {color};padding:12px 16px;background:#111827;border-radius:8px">
<div style="font-size:18px"><b>{icon} {html.escape(heading)}</b></div>
<div style="font-size:16px;margin-top:7px"><b>MEP #{issue['id']} — {html.escape(issue['subject'])}</b></div>
<table style="margin-top:10px">{rows_html}</table>
<div style="margin-top:12px">{links}</div>
</div>'''
    return plain, formatted

def issue_schedule(issue: dict[str, Any], lang: str | None = None) -> str:
    lang = lang or communication_language()
    date = issue.get("start_date") or tr("Date à préciser", "Date to be confirmed", lang)
    start = issue.get("start_time")
    end = issue.get("end_time")
    if start and end: return f"{date} · {start}–{end}"
    if start: return f"{date} · {start}"
    return f"{date} · {tr('Heure à préciser','Time to be confirmed',lang)}"

async def matrix_send(issue: dict[str, Any], kind: str, force: bool = False) -> dict[str, Any]:
    cfg = matrix_config()
    if not force and not cfg["enabled"]:
        return {"sent": False, "disabled": True}
    if not cfg["homeserver"] or not cfg["access_token"] or not cfg["room_id"]:
        raise RuntimeError("Matrix configuration is incomplete")
    body, formatted = matrix_message(issue, kind)
    txn_id = f"mep-{issue['id']}-{int(time.time()*1000)}-{uuid.uuid4().hex[:8]}"
    room = quote(cfg["room_id"], safe="")
    url = f'{cfg["homeserver"]}/_matrix/client/v3/rooms/{room}/send/m.room.message/{txn_id}'
    payload = {"msgtype":"m.notice", "body":body, "format":"org.matrix.custom.html", "formatted_body":formatted}
    headers = {"Authorization": f'Bearer {cfg["access_token"]}', "Content-Type":"application/json"}
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.put(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    return {"sent": True, "event_id": data.get("event_id"), "room_id": cfg["room_id"]}

async def maybe_matrix(issue: dict[str, Any], kind: str) -> None:
    cfg = matrix_config()
    enabled_for_kind = {"new":cfg["notify_new"], "changed":cfg["notify_changed"], "daily":cfg["notify_daily"]}.get(kind, False)
    if not cfg["enabled"] or not enabled_for_kind:
        return
    try:
        result = await matrix_send(issue, kind)
        record(issue['id'], issue_version(issue), f"matrix_{kind}", f"Matrix: {kind}", [cfg['room_id']], 'sent', message_id=result.get('event_id',''), manual=False, pdf=False)
    except Exception as exc:
        record(issue['id'], issue_version(issue), f"matrix_{kind}", f"Matrix: {kind}", [cfg.get('room_id','')], 'error', error=str(exc), manual=False, pdf=False)
        print(f"Erreur Matrix MEP #{issue['id']}: {exc}", flush=True)

def smtp_send(subject:str,html_body:str,recipients:list[str],attachment:bytes|None=None,filename:str|None=None,lang:str|None=None,calendar_data:bytes|None=None,calendar_filename:str|None=None,calendar_method:str="REQUEST")->str:
    cfg=runtime_config()
    if not cfg["smtp_enabled"]:raise RuntimeError('SMTP désactivé dans .env')
    if not SMTP_HOST:raise RuntimeError('SMTP_HOST non configuré')
    if not recipients:raise RuntimeError('Aucun destinataire')
    msg=EmailMessage(); msg['Subject']=subject; msg['From']=cfg['smtp_from']; msg['To']=', '.join(recipients); msg['Message-ID']=f"<{hashlib.sha256((subject+str(now_local().timestamp())).encode()).hexdigest()[:24]}@mep-planner>"
    lang=lang or communication_language()
    msg.set_content(f"{subject}\n\n{tr('Cette communication a été envoyée par MEP Planner. Consultez la version HTML ou la fiche PDF jointe.','This communication was sent by MEP Planner. See the HTML version or the attached PDF sheet.',lang)}")
    msg.add_alternative(html_body,subtype='html')
    logo=brand_logo_bytes()
    if logo:
        subtype='png'; suffix=BRAND_LOGO_PATH.suffix.lower()
        if suffix in {'.jpg','.jpeg'}:subtype='jpeg'
        elif suffix=='.gif':subtype='gif'
        msg.get_payload()[-1].add_related(logo,maintype='image',subtype=subtype,cid='<mep-planner-logo>',filename=BRAND_LOGO_PATH.name,disposition='inline')
    company_logo=company_logo_bytes()
    if company_logo:
        msg.get_payload()[-1].add_related(company_logo,maintype='image',subtype='png',cid='<company-logo>',filename='company-logo.png',disposition='inline')
    if attachment:msg.add_attachment(attachment,maintype='application',subtype='pdf',filename=filename or 'rapport-mep.pdf')
    if calendar_data:
        msg.add_attachment(calendar_data, maintype='text', subtype='calendar', filename=calendar_filename or 'mep-invitation.ics', params={'method': calendar_method, 'charset': 'UTF-8'})
    if cfg['smtp_security']=='ssl':
        with smtplib.SMTP_SSL(cfg['smtp_host'],cfg['smtp_port'],timeout=cfg['smtp_timeout_seconds'],context=ssl.create_default_context()) as smtp:
            if cfg['smtp_username']:smtp.login(cfg['smtp_username'],cfg['smtp_password'])
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(cfg['smtp_host'],cfg['smtp_port'],timeout=cfg['smtp_timeout_seconds']) as smtp:
            smtp.ehlo()
            if cfg['smtp_security']=='starttls':smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
            if cfg['smtp_username']:smtp.login(cfg['smtp_username'],cfg['smtp_password'])
            smtp.send_message(msg)
    return str(msg['Message-ID'])

def already_sent(issue_id:int|None,version:str,kind:str,recipients:list[str])->bool:
    with db() as con:return con.execute("SELECT 1 FROM notifications WHERE issue_id IS ? AND issue_version=? AND notification_type=? AND recipient_key=? AND manual=0 AND status='sent' LIMIT 1",(issue_id,version,kind,recipient_key(recipients))).fetchone() is not None

def record(issue_id,version,kind,subject,recipients,status,error='',message_id='',manual=False,pdf=False):
    with db() as con: con.execute('INSERT INTO notifications(issue_id,issue_version,notification_type,subject,recipients,recipient_key,sent_at,status,error,message_id,manual,pdf_attached) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(issue_id,version,kind,subject,';'.join(recipients),recipient_key(recipients),now_local().isoformat(timespec='seconds'),status,error,message_id,int(manual),int(pdf)))

def deliver(issue:dict[str,Any],kind:str,subject:str,intro:str,recipients:list[str],manual=False,include_pdf=True,note='',include_calendar=True)->dict[str,Any]:
    version=issue_version(issue)
    if not manual and already_sent(issue['id'],version,kind,recipients):return {'sent':False,'duplicate':True}
    try:
        lang=communication_language();pdf=report_pdf(issue,lang=lang) if include_pdf else None;filename=f"{'release-sheet' if lang=='en' else 'fiche-mep'}-{issue['id']}.pdf" if pdf else None;calendar_data=calendar_invitation(issue,recipients,'REQUEST',lang) if include_calendar else None;calendar_filename=f"mep-{issue['id']}.ics" if calendar_data else None;message_id=smtp_send(subject,email_template(subject,intro,[issue],note,lang),recipients,pdf,filename,lang,calendar_data,calendar_filename,'REQUEST');record(issue['id'],version,kind,subject,recipients,'sent',message_id=message_id,manual=manual,pdf=bool(pdf));return {'sent':True,'duplicate':False}
    except Exception as exc:
        record(issue['id'],version,kind,subject,recipients,'error',error=str(exc),manual=manual,pdf=include_pdf);raise

def issue_by_id(issue_id:int)->dict[str,Any]:
    issue=next((i for i in cache.get('issues',[]) if i.get('id')==issue_id),None)
    if not issue:raise HTTPException(404,'MEP introuvable')
    return issue

def notification_summary(issue_id:int)->dict[str,Any]:
    with db() as con: rows=con.execute('SELECT * FROM notifications WHERE issue_id=? ORDER BY sent_at DESC',(issue_id,)).fetchall()
    if not rows:return {'sent':False,'last':None,'count':0,'recipients':[],'errors':0}
    successful=[r for r in rows if r['status']=='sent'];last=successful[0] if successful else rows[0]
    return {'sent':bool(successful),'last':dict(last),'count':len(successful),'recipients':last['recipients'].split(';') if last['recipients'] else [],'errors':sum(r['status']=='error' for r in rows)}

async def send_change_notifications(previous,current,issues):
    if not previous or not SMTP_ENABLED or not SMTP_RECIPIENTS:return
    by_id={str(i['id']):i for i in issues}
    for key in [k for k in current if k not in previous]:
        try: await asyncio.to_thread(deliver,by_id[key],'new',f"{tr('Nouvelle MEP planifiée','New scheduled release')} - #{key}",tr('Une nouvelle mise en production a été détectée.','A new production release has been detected.'),SMTP_RECIPIENTS,False,True,'')
        except Exception as e:print(f'Erreur SMTP nouvelle MEP #{key}: {e}',flush=True)
        await maybe_matrix(by_id[key], 'new')
    for key in [k for k in current if k in previous and current[k]!=previous[k]]:
        try: await asyncio.to_thread(deliver,by_id[key],'changed',f"{tr('MEP modifiée','Release updated')} - #{key}",tr('Les informations de cette MEP ont été modifiées.','The information for this release has been updated.'),SMTP_RECIPIENTS,False,True,'')
        except Exception as e:print(f'Erreur SMTP modification MEP #{key}: {e}',flush=True)
        await maybe_matrix(by_id[key], 'changed')

async def synchronize(initial=False):
    global cache
    if sync_lock.locked():return
    async with sync_lock:
        cache['last_attempt']=now_local().isoformat(timespec='seconds')
        log_event('redmine','info','Synchronization started', f'initial={initial}')
        try:
            mode,issues,pages,tickets=await fetch_redmine();previous=load_json(STATE_FILE,{});current={str(i['id']):issue_signature(i) for i in issues};cache={'mode':mode,'issues':issues,'last_sync':now_local().isoformat(timespec='seconds'),'last_attempt':cache['last_attempt'],'error':None,'pages_read':pages,'tickets_read':tickets};save_json(STATE_FILE,current)
            log_event('redmine','success','Synchronization completed', f'mode={mode}; pages={pages}; tickets={tickets}; mep={len(issues)}')
            if not initial:await send_change_notifications(previous,current,issues)
        except Exception as e:
            cache['error']=f'{type(e).__name__}: {e}'
            log_event('redmine','error','Synchronization failed', cache['error'])
            print(f"Erreur synchronisation Redmine : {cache['error']}",flush=True)

async def watcher():
    await synchronize(initial=True)
    while True:await asyncio.sleep(POLL_INTERVAL);await synchronize(False)

async def daily_mailer():
    while True:
        now=now_local();target=now.replace(hour=DAILY_EMAIL_HOUR,minute=DAILY_EMAIL_MINUTE,second=0,microsecond=0)
        if target<=now:target+=timedelta(days=1)
        await asyncio.sleep(max(1,(target-now).total_seconds()))
        if not DAILY_EMAIL_ENABLED or not SMTP_ENABLED or not SMTP_RECIPIENTS:continue
        today=now_local().date().isoformat()
        for issue in [i for i in cache.get('issues',[]) if i.get('start_date')==today and not is_done(i)]:
            try:await asyncio.to_thread(deliver,issue,'daily',f"{tr('MEP du jour',"Today's release")} - #{issue['id']}",tr('Rappel de la mise en production prévue aujourd’hui.',"Reminder for today's scheduled production release."),SMTP_RECIPIENTS,False,True,'')
            except Exception as e:print(f"Erreur e-mail quotidien #{issue['id']}: {e}",flush=True)
            await maybe_matrix(issue, 'daily')

@app.on_event('startup')
async def startup():init_db();asyncio.create_task(watcher());asyncio.create_task(daily_mailer())

@app.get('/api/health')
async def health():return {'status':'ok','version':APP_VERSION,'mode':cache['mode'],'syncing':sync_lock.locked(),'last_sync':cache['last_sync'],'last_attempt':cache['last_attempt'],'pages_read':cache['pages_read'],'tickets_read':cache['tickets_read'],'mep_count':len(cache.get('issues',[])),'error':cache['error']}

@app.get('/api/issues')
async def issues(authorization: str | None = Header(default=None)):
    current_user(authorization)
    data=[]
    for issue in cache.get('issues',[]):data.append({**issue,'priority_level':priority_level(issue),'notification':notification_summary(issue['id'])})
    return {'mode':cache['mode'],'syncing':sync_lock.locked(),'last_sync':cache['last_sync'],'issues':[i for i in data if not is_done(i)],'history':[i for i in data if is_done(i)],'error':cache['error']}

@app.post('/api/refresh')
async def refresh(authorization: str | None = Header(default=None)):
    current_user(authorization)
    if not sync_lock.locked():asyncio.create_task(synchronize(False))
    return {'status':'accepted','syncing':True}

@app.get('/api/notifications')
async def notifications(issue_id:int|None=None,limit:int=Query(200,ge=1,le=1000),authorization: str | None = Header(default=None)):
    current_user(authorization)
    with db() as con:
        if issue_id is None:rows=con.execute('SELECT * FROM notifications ORDER BY sent_at DESC LIMIT ?',(limit,)).fetchall()
        else:rows=con.execute('SELECT * FROM notifications WHERE issue_id=? ORDER BY sent_at DESC LIMIT ?',(issue_id,limit)).fetchall()
    return {'notifications':[dict(r) for r in rows]}

@app.post('/api/issues/{issue_id}/resend')
async def resend(issue_id:int,payload:ResendRequest,authorization: str | None = Header(default=None)):
    current_user(authorization)
    issue=issue_by_id(issue_id);recipients=[str(x) for x in payload.recipients] if payload.recipients else [v.strip() for v in runtime_config()['smtp_recipients'].split(';') if v.strip()]
    if not recipients:raise HTTPException(400,'Aucun destinataire configuré')
    try:return await asyncio.to_thread(deliver,issue,'manual',f"{tr('Renvoi communication MEP','Release communication resend')} - #{issue_id}",tr('Renvoi manuel demandé depuis MEP Planner.','Manual resend requested from MEP Planner.'),recipients,True,payload.include_pdf,payload.note,payload.include_calendar)
    except Exception as e:raise HTTPException(502,str(e)) from e

@app.post('/api/admin/login')
async def admin_login(payload: AdminLoginRequest):
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=503, detail="ADMIN_PASSWORD is not configured")
    if not secrets.compare_digest(payload.password, ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Invalid administrator password")
    token, expires_at = create_admin_session()
    return {"token": token, "expires_at": expires_at}

@app.get('/api/admin/session')
async def admin_session(authorization: str | None = Header(default=None)):
    require_admin(authorization)
    return {"authenticated": True}

@app.get('/api/version/check')
async def version_check():
    result = await github_version_status()
    result['preserved_paths'] = ['.env','data/','logs/','backups/','docker-compose.override.yml']
    result['update_command'] = './scripts/update.sh'
    return result

def _human_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(max(0, value))
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} TB"

def _dir_size(path: Path) -> int:
    total = 0
    if not path.exists(): return 0
    for item in path.rglob('*'):
        try:
            if item.is_file(): total += item.stat().st_size
        except OSError: pass
    return total

def _backup_files() -> list[dict[str, Any]]:
    rows=[]
    for item in sorted(BACKUP_DIR.glob('mep-planner-backup-*.zip'), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            rows.append({'name':item.name,'size':item.stat().st_size,'size_human':_human_bytes(item.stat().st_size),'created_at':datetime.fromtimestamp(item.stat().st_mtime,TIMEZONE).isoformat(timespec='seconds')})
        except OSError: pass
    return rows

def _safe_backup_path(name: str) -> Path:
    clean=Path(name).name
    if clean != name or not clean.startswith('mep-planner-backup-') or not clean.endswith('.zip'):
        raise HTTPException(400,'Invalid backup name')
    path=BACKUP_DIR/clean
    if not path.exists(): raise HTTPException(404,'Backup not found')
    return path

def _create_backup(name: str='', include_logs: bool=False) -> Path:
    stamp=now_local().strftime('%Y%m%d-%H%M%S')
    suffix=re.sub(r'[^A-Za-z0-9_-]+','-',name.strip()).strip('-')[:40]
    filename=f"mep-planner-backup-{stamp}{('-'+suffix) if suffix else ''}.zip"
    target=BACKUP_DIR/filename
    manifest={'format_version':1,'application':'MEP Planner','app_version':APP_VERSION,'created_at':now_local().isoformat(timespec='seconds'),'includes':{'data':True,'branding':True,'logs':include_logs}}
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for base,label in [(DATA_DIR,'data'),(Path('/app/branding'),'branding')]:
            if base.exists():
                for item in base.rglob('*'):
                    if item.is_file(): archive.write(item,Path(label)/item.relative_to(base))
        if include_logs and LOG_DIR.exists():
            for item in LOG_DIR.rglob('*'):
                if item.is_file(): archive.write(item,Path('logs')/item.relative_to(LOG_DIR))
        archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    with zipfile.ZipFile(target,'a',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('checksum.sha256',digest+'  '+filename+'\n')
    return target

def _validate_backup(path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            names=archive.namelist()
            if 'manifest.json' not in names: raise HTTPException(400,'Missing backup manifest')
            for name in names:
                candidate=Path(name)
                if candidate.is_absolute() or '..' in candidate.parts: raise HTTPException(400,'Unsafe archive path')
            manifest=json.loads(archive.read('manifest.json'))
            if manifest.get('application')!='MEP Planner': raise HTTPException(400,'This archive is not a MEP Planner backup')
            return manifest
    except zipfile.BadZipFile:
        raise HTTPException(400,'Invalid ZIP archive')

@app.get('/api/system/health-details')
async def health_details(authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    cfg=runtime_config(); checks={}; alerts=[]
    try:
        with db() as con: con.execute('SELECT 1').fetchone()
        checks['database']={'status':'ok','label':'Base de données'}
    except Exception as exc:
        checks['database']={'status':'error','label':'Base de données','detail':str(exc)}; alerts.append('Base de données inaccessible')
    checks['api']={'status':'ok','label':'API'}
    checks['scheduler']={'status':'ok','label':'Planificateur'}
    for key,enabled,label in [('smtp',bool(cfg.get('smtp_enabled') and cfg.get('smtp_host')),'SMTP'),('ldap',bool(cfg.get('ldap_enabled')),'LDAP'),('redmine',bool(cfg.get('redmine_url')),'Redmine')]:
        checks[key]={'status':'configured' if enabled else 'disabled','label':label}
    disk=shutil.disk_usage(DATA_DIR); disk_percent=round((disk.used/disk.total)*100,1) if disk.total else 0
    if disk_percent>=90: alerts.append('Espace disque critique')
    backups=_backup_files(); last_backup=backups[0] if backups else None
    if not backups: alerts.append('Aucune sauvegarde disponible')
    score=100
    score-=sum(20 for c in checks.values() if c['status']=='error')
    if not backups: score-=10
    if disk_percent>=90: score-=20
    elif disk_percent>=80: score-=10
    if cache.get('error'): score-=10; alerts.append('Dernière synchronisation Redmine en erreur')
    uptime=None
    try:
        uptime=int(float(Path('/proc/uptime').read_text().split()[0]))
    except Exception: pass
    return {'status':'ok' if score>=80 else ('warning' if score>=50 else 'error'),'score':max(0,score),'version':APP_VERSION,'checks':checks,'resources':{'disk_percent':disk_percent,'disk_used':_human_bytes(disk.used),'disk_total':_human_bytes(disk.total),'database_size':_human_bytes(DB_FILE.stat().st_size if DB_FILE.exists() else 0),'backups_size':_human_bytes(_dir_size(BACKUP_DIR)),'backup_count':len(backups),'uptime_seconds':uptime,'platform':platform.system()},'last_backup':last_backup,'last_sync':cache.get('last_sync'),'last_error':cache.get('error'),'alerts':alerts}

@app.get('/api/backups')
async def list_backups(authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    return {'backups':_backup_files(),'directory':str(BACKUP_DIR)}

@app.post('/api/backups')
async def create_backup(payload: BackupCreateRequest, authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    path=await asyncio.to_thread(_create_backup,payload.name,payload.include_logs)
    return {'created':True,'backup':next(x for x in _backup_files() if x['name']==path.name)}

@app.get('/api/backups/{name}/download')
async def download_backup(name: str, authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    path=_safe_backup_path(name)
    return FileResponse(path,media_type='application/zip',filename=path.name)

@app.delete('/api/backups/{name}')
async def delete_backup(name: str, authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization); path=_safe_backup_path(name); path.unlink(); return {'deleted':True}

@app.post('/api/backups/import')
async def import_backup(file: UploadFile = File(...), authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    if not file.filename or not file.filename.lower().endswith('.zip'): raise HTTPException(400,'A ZIP file is required')
    stamp=now_local().strftime('%Y%m%d-%H%M%S'); target=BACKUP_DIR/f'mep-planner-backup-{stamp}-imported.zip'
    total=0
    with target.open('wb') as output:
        while chunk:=await file.read(1024*1024):
            total+=len(chunk)
            if total>512*1024*1024: target.unlink(missing_ok=True); raise HTTPException(413,'Backup exceeds 512 MB')
            output.write(chunk)
    try: manifest=_validate_backup(target)
    except Exception: target.unlink(missing_ok=True); raise
    return {'imported':True,'name':target.name,'manifest':manifest}

@app.post('/api/backups/restore')
async def restore_backup(payload: RestoreRequest, authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization); source=_safe_backup_path(payload.backup_name); manifest=_validate_backup(source)
    safety=await asyncio.to_thread(_create_backup,'before-restore',False)
    with tempfile.TemporaryDirectory(prefix='mep-restore-') as tmp:
        root=Path(tmp)
        with zipfile.ZipFile(source) as archive: archive.extractall(root)
        if payload.restore_database and (root/'data'/DB_FILE.name).exists(): shutil.copy2(root/'data'/DB_FILE.name,DB_FILE)
        if payload.restore_settings:
            for name in ['issues_state.json']:
                src=root/'data'/name
                if src.exists(): shutil.copy2(src,DATA_DIR/name)
        if payload.restore_branding:
            src=root/'data'/'branding'
            if src.exists():
                if BRANDING_DIR.exists(): shutil.rmtree(BRANDING_DIR)
                shutil.copytree(src,BRANDING_DIR)
        if payload.restore_logs and (root/'logs').exists():
            LOG_DIR.mkdir(parents=True,exist_ok=True)
            shutil.copytree(root/'logs',LOG_DIR,dirs_exist_ok=True)
    return {'restored':True,'manifest':manifest,'safety_backup':safety.name,'restart_required':True}

@app.get('/api/settings')
async def get_settings(authorization: str | None = Header(default=None)):
    current_user(authorization)
    return branding_settings()

@app.put('/api/settings')
async def update_settings(payload: BrandingSettings, authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    accent=payload.company_accent.strip()
    if accent and not re.fullmatch(r"#[0-9A-Fa-f]{6}",accent):
        raise HTTPException(400,"La couleur doit être au format #RRGGBB")
    values=payload.model_dump()
    token = values.pop("matrix_access_token", "").strip()
    for key,value in values.items():
        if isinstance(value, bool):
            set_setting(key, str(value).lower())
        else:
            set_setting(key,str(value).strip())
    if token:
        set_setting("matrix_access_token", token)
    return branding_settings()

@app.post('/api/settings/matrix/test')
async def test_matrix(authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    sample = {
        "id": 0, "subject": tr("Test de notification Matrix", "Matrix notification test"),
        "start_date": now_local().date().isoformat(), "start_time": now_local().strftime("%H:%M"),
        "end_time": (now_local()+timedelta(hours=1)).strftime("%H:%M"), "environment":"TEST",
        "priority":"Normal", "status":tr("Test", "Test"), "assigned_to":"MEP Planner",
        "url": GITHUB_REPOSITORY_URL, "estimated_hours":1, "description":""
    }
    try:
        return await matrix_send(sample, "test", force=True)
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc

@app.post('/api/settings/company-logo')
async def upload_company_logo(file: UploadFile = File(...), authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    if file.content_type != "image/png":
        raise HTTPException(400,"Format accepté : PNG uniquement")
    content=await file.read()
    if len(content)>3*1024*1024:
        raise HTTPException(400,"Logo trop volumineux (maximum 3 Mo)")
    COMPANY_LOGO_FILE.write_bytes(content)
    return {"status":"ok","company_logo_configured":True}

@app.delete('/api/settings/company-logo')
async def delete_company_logo(authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    COMPANY_LOGO_FILE.unlink(missing_ok=True)
    return {"status":"ok","company_logo_configured":False}

@app.get('/api/settings/company-logo')
async def serve_company_logo():
    if not COMPANY_LOGO_FILE.is_file():
        raise HTTPException(404,"Aucun logo entreprise")
    return Response(COMPANY_LOGO_FILE.read_bytes(),media_type='image/png',headers={'Cache-Control':'no-store'})

BRANDING_ASSETS = {
    "logo-dark": (COMPANY_LOGO_DARK_FILE, {"image/png"}, 3 * 1024 * 1024),
    "favicon": (COMPANY_FAVICON_FILE, {"image/png", "image/x-icon", "image/vnd.microsoft.icon"}, 1024 * 1024),
    "login-background": (LOGIN_BACKGROUND_FILE, {"image/webp", "image/png", "image/jpeg"}, 8 * 1024 * 1024),
}

@app.post('/api/settings/branding/{asset}')
async def upload_branding_asset(asset: str, file: UploadFile = File(...), authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    if asset not in BRANDING_ASSETS: raise HTTPException(404, 'Unknown branding asset')
    path, allowed_types, max_size = BRANDING_ASSETS[asset]
    if file.content_type not in allowed_types: raise HTTPException(400, 'Unsupported image format')
    content = await file.read()
    if len(content) > max_size: raise HTTPException(413, 'Image is too large')
    path.write_bytes(content)
    log_event('application','success','Branding asset updated',asset)
    return {'ok': True, 'asset': asset}

@app.get('/api/settings/branding/{asset}')
async def serve_branding_asset(asset: str):
    if asset not in BRANDING_ASSETS: raise HTTPException(404, 'Unknown branding asset')
    path, _, _ = BRANDING_ASSETS[asset]
    if not path.is_file(): raise HTTPException(404, 'Branding asset not configured')
    media = 'image/webp' if path.suffix == '.webp' else 'image/png'
    return Response(path.read_bytes(), media_type=media, headers={'Cache-Control':'no-store'})

@app.delete('/api/settings/branding/{asset}')
async def delete_branding_asset(asset: str, authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    if asset not in BRANDING_ASSETS: raise HTTPException(404, 'Unknown branding asset')
    BRANDING_ASSETS[asset][0].unlink(missing_ok=True)
    return {'ok': True, 'asset': asset}

@app.get('/api/issues/{issue_id}/report.pdf')
async def pdf_report(issue_id:int):
    issue=issue_by_id(issue_id);content=await asyncio.to_thread(report_pdf,issue,None,communication_language())
    return Response(content,media_type='application/pdf',headers={'Content-Disposition':f'inline; filename="MEP-{issue_id}.pdf"'})


@app.get('/api/admin/configuration')
async def get_admin_configuration(authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    return public_runtime_config()

@app.get('/api/admin/logs')
async def admin_logs(system: str = Query('redmine'), limit: int = Query(200, ge=1, le=1000), authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    selected = (system or 'redmine').lower()
    allowed = {'redmine','smtp','matrix','ldap','oidc','authentication','application'}
    if selected not in allowed:
        raise HTTPException(400, 'Unsupported log type')
    if selected == 'smtp':
        with db() as con:
            rows=con.execute('SELECT id,sent_at AS occurred_at,status AS level,notification_type AS message,error AS details,subject,recipients FROM notifications ORDER BY sent_at DESC LIMIT ?', (limit,)).fetchall()
        return {'system':selected,'logs':[dict(r) for r in rows]}
    with db() as con:
        rows=con.execute('SELECT id,occurred_at,system,level,message,details FROM system_logs WHERE system=? ORDER BY occurred_at DESC LIMIT ?', (selected,limit)).fetchall()
    return {'system':selected,'logs':[dict(r) for r in rows]}

@app.put('/api/admin/configuration')
async def save_admin_configuration(payload: InfrastructureSettings, authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    values = payload.model_dump()
    for secret in ("redmine_api_key","smtp_password","ldap_bind_password","oidc_client_secret"):
        value = str(values.pop(secret, "")).strip()
        if value: set_setting(secret, value)
    values.pop("ldap_ca_configured", None)
    for key, value in values.items(): set_setting(key, str(value).lower() if isinstance(value,bool) else str(value).strip())
    return public_runtime_config()

@app.post('/api/admin/redmine/test')
async def test_redmine_configuration(authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization); cfg=runtime_config()
    log_event('redmine','info','Connection test started', cfg.get('redmine_url',''))
    if not cfg['redmine_url'] or not cfg['redmine_api_key']: raise HTTPException(400,'Redmine URL and API key are required')
    try:
        async with httpx.AsyncClient(timeout=cfg['redmine_timeout_seconds'], verify=cfg['redmine_verify_tls']) as client:
            r=await client.get(cfg['redmine_url']+'/users/current.json', headers={'X-Redmine-API-Key':cfg['redmine_api_key']}); r.raise_for_status(); user=r.json().get('user',{})
        await synchronize(False)
        if cache.get('error'):
            raise RuntimeError(cache['error'])
        log_event('redmine','success','Connection test successful', f"user={user.get('login') or user.get('firstname','')}; server={cfg['redmine_url']}")
        return {'ok':True,'status':'connected','user':user.get('login') or user.get('firstname',''),'display_name':' '.join(v for v in [user.get('firstname',''),user.get('lastname','')] if v).strip(),'server':cfg['redmine_url'],'message':'Redmine connection successful','sync':{'mep_count':len(cache.get('issues',[])),'tickets_read':cache.get('tickets_read',0),'last_sync':cache.get('last_sync')}}
    except Exception as exc:
        log_event('redmine','error','Connection test failed', f'{type(exc).__name__}: {exc}')
        raise HTTPException(502,str(exc))

@app.post('/api/admin/smtp/test')
async def test_smtp_configuration(authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization); cfg=runtime_config(); recipients=[v.strip() for v in cfg['smtp_recipients'].split(';') if v.strip()]
    if not recipients: raise HTTPException(400,'Configure at least one SMTP recipient')
    try:
        log_event('smtp','info','SMTP test started', ';'.join(recipients))
        message_id=await asyncio.to_thread(smtp_send, tr('Test SMTP MEP Planner','MEP Planner SMTP test'), '<h2>MEP Planner</h2><p>SMTP configuration is working.</p>', recipients)
        log_event('smtp','success','SMTP test successful', message_id)
        return {'ok':True,'message_id':message_id}
    except Exception as exc:
        log_event('smtp','error','SMTP test failed', f'{type(exc).__name__}: {exc}')
        raise HTTPException(502,str(exc))


def ldap_server(cfg: dict[str, Any]):
    from ldap3 import Server, Tls, ALL
    validate = ssl.CERT_REQUIRED if cfg.get('ldap_verify_tls', True) else ssl.CERT_NONE
    tls = Tls(validate=validate, ca_certs_file=str(LDAP_CA_FILE) if LDAP_CA_FILE.exists() else None)
    url = str(cfg.get('ldap_url','')).strip()
    use_ssl = url.lower().startswith('ldaps://')
    host = re.sub(r'^ldaps?://', '', url, flags=re.I).split('/')[0].split(':')[0]
    port = int(cfg.get('ldap_port') or (636 if use_ssl else 389))
    return Server(host, port=port, use_ssl=use_ssl, get_info=ALL, tls=tls, connect_timeout=10)

def ldap_entry_value(entry, name: str) -> str:
    try:
        value = entry[name].value
        if isinstance(value, list): return str(value[0] if value else '')
        return str(value or '')
    except Exception:
        return ''

def ldap_group_names(conn, cfg: dict[str, Any], user_dn: str, username: str) -> list[str]:
    from ldap3 import SUBTREE
    base = cfg.get('ldap_group_base_dn') or cfg.get('ldap_base_dn')
    if not base: return []
    ref_attr = cfg.get('ldap_reference_attribute') or 'dn'
    reference = user_dn if ref_attr.lower() in {'dn','distinguishedname'} else username
    member_attr = cfg.get('ldap_group_member_attribute') or 'member'
    template = cfg.get('ldap_group_filter') or '({member_attribute}={reference})'
    filt = template.replace('%{ref}', reference).replace('{reference}', reference).replace('{user_dn}', user_dn).replace('{username}', username).replace('{member_attribute}', member_attr)
    obj = cfg.get('ldap_group_object_class') or ''
    if obj and 'objectClass' not in filt: filt = f'(&(objectClass={obj}){filt})'
    name_attr = cfg.get('ldap_group_name_attribute') or 'cn'
    conn.search(base, filt, SUBTREE, attributes=[name_attr], size_limit=500)
    return [ldap_entry_value(e, name_attr) for e in conn.entries if ldap_entry_value(e, name_attr)]

def parse_ldap_group_map(raw: str) -> dict[str, str]:
    """Parse `group:user;admins:admin`; last duplicate wins."""
    result: dict[str, str] = {}
    for item in re.split(r"[;\n]+", raw or ""):
        item = item.strip()
        if not item: continue
        group, sep, role = item.partition(":")
        group, role = group.strip(), role.strip().lower()
        if group and sep and role in {"user", "admin"}:
            result[group.casefold()] = role
    return result

def ldap_authenticate_and_profile(username: str, password: str, cfg: dict[str, Any]) -> dict[str, Any] | None:
    from ldap3 import Connection, SUBTREE
    server = ldap_server(cfg)
    bind = Connection(server, user=cfg.get('ldap_bind_dn') or None, password=cfg.get('ldap_bind_password') or None, auto_bind=True)
    safe = username.replace('\\','').replace('*','').replace('(','').replace(')','')
    filt = (cfg.get('ldap_user_filter') or '(&(objectClass=person)(uid={username}))').replace('%{username}', safe).replace('{username}', safe)
    attrs = list(dict.fromkeys([cfg.get('ldap_login_attribute','uid'), cfg.get('ldap_name_attribute','givenName'), cfg.get('ldap_last_name_attribute','sn'), cfg.get('ldap_email_attribute','mail')]))
    bind.search(cfg.get('ldap_base_dn',''), filt, SUBTREE, attributes=attrs, size_limit=2)
    if len(bind.entries) != 1:
        bind.unbind(); return None
    entry=bind.entries[0]; user_dn=entry.entry_dn
    groups=ldap_group_names(bind,cfg,user_dn,username)
    mapping=parse_ldap_group_map(str(cfg.get('ldap_group_map') or ''))
    matched_roles={mapping[g.casefold()] for g in groups if g.casefold() in mapping}
    # When a mapping is configured, membership in at least one mapped group is mandatory.
    if mapping and not matched_roles:
        bind.unbind(); return None
    bind.unbind()
    auth=Connection(server,user=user_dn,password=password,auto_bind=True); ok=bool(auth.bound); auth.unbind()
    if not ok: return None
    first=ldap_entry_value(entry,cfg.get('ldap_name_attribute','givenName')); last=ldap_entry_value(entry,cfg.get('ldap_last_name_attribute','sn'))
    role='admin' if 'admin' in matched_roles else 'user'
    return {'username':ldap_entry_value(entry,cfg.get('ldap_login_attribute','uid')) or username,'dn':user_dn,'display_name':(' '.join(x for x in [first,last] if x)).strip() or username,'email':ldap_entry_value(entry,cfg.get('ldap_email_attribute','mail')),'groups':groups,'matched_groups':[g for g in groups if g.casefold() in mapping],'role':role}

@app.post('/api/admin/ldap/ca-certificate')
async def upload_ldap_ca_certificate(file: UploadFile = File(...), authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    data=await file.read()
    if len(data)>2_000_000: raise HTTPException(413,'Certificate file is too large')
    text=data.decode('utf-8','ignore')
    if 'BEGIN CERTIFICATE' not in text: raise HTTPException(400,'A PEM encoded certificate is required')
    LDAP_CA_FILE.write_text(text)
    log_event('ldap','success','LDAP CA certificate imported',file.filename or '')
    return {'ok':True,'filename':file.filename,'configured':True}

@app.delete('/api/admin/ldap/ca-certificate')
async def delete_ldap_ca_certificate(authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    LDAP_CA_FILE.unlink(missing_ok=True)
    return {'ok':True}

@app.get('/api/admin/ldap/groups')
async def discover_ldap_groups(authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization); cfg=runtime_config()
    from ldap3 import Connection, SUBTREE
    conn=Connection(ldap_server(cfg),user=cfg.get('ldap_bind_dn') or None,password=cfg.get('ldap_bind_password') or None,auto_bind=True)
    attr=cfg.get('ldap_group_name_attribute') or 'cn'; obj=cfg.get('ldap_group_object_class') or 'groupOfNames'
    conn.search(cfg.get('ldap_group_base_dn') or cfg.get('ldap_base_dn'),f'(objectClass={obj})',SUBTREE,attributes=[attr],size_limit=500)
    groups=sorted({ldap_entry_value(e,attr) for e in conn.entries if ldap_entry_value(e,attr)},key=str.casefold); conn.unbind()
    return {'groups':groups}

@app.post('/api/admin/ldap/test')
async def test_ldap_configuration(authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization); cfg=runtime_config()
    try:
        from ldap3 import Connection
        server=ldap_server(cfg)
        conn=Connection(server, user=cfg['ldap_bind_dn'] or None, password=cfg['ldap_bind_password'] or None, auto_bind=True)
        info={'ok':True,'server':str(server.host),'vendor':str(getattr(server.info,'vendor_name','') or '')}; conn.unbind(); log_event('ldap','success','LDAP connection test successful', str(info)); return info
    except Exception as exc:
        log_event('ldap','error','LDAP connection test failed', f'{type(exc).__name__}: {exc}')
        raise HTTPException(502,str(exc))

@app.post('/api/admin/ldap/search')
async def search_ldap(payload: LdapSearchRequest, authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization); cfg=runtime_config()
    try:
        from ldap3 import Connection, SUBTREE
        server=ldap_server(cfg); conn=Connection(server,user=cfg['ldap_bind_dn'] or None,password=cfg['ldap_bind_password'] or None,auto_bind=True)
        q=(payload.query or '').replace('\\','').replace('*','')
        attr=cfg['ldap_login_attribute']; filt=f'(|({attr}=*{q}*)({cfg["ldap_name_attribute"]}=*{q}*)({cfg["ldap_email_attribute"]}=*{q}*))'
        base=payload.group_dn or cfg['ldap_base_dn']; attrs=list(dict.fromkeys([attr,cfg['ldap_name_attribute'],cfg.get('ldap_last_name_attribute','sn'),cfg['ldap_email_attribute']]))
        conn.search(base, filt, SUBTREE, attributes=attrs, size_limit=100)
        rows=[]
        for e in conn.entries:
            def av(name):
                try:return str(e[name].value or '')
                except:return ''
            rows.append({'dn':e.entry_dn,'username':av(attr),'display_name':(' '.join(x for x in [av(cfg['ldap_name_attribute']),av(cfg.get('ldap_last_name_attribute','sn'))] if x)).strip(),'email':av(cfg['ldap_email_attribute'])})
        conn.unbind(); return {'entries':rows}
    except Exception as exc: raise HTTPException(502,str(exc))

@app.post('/api/admin/ldap/import')
async def import_ldap(payload: LdapImportRequest, authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization); role=payload.role if payload.role in {'user','admin'} else 'user'; now=now_local().isoformat(timespec='seconds'); imported=0
    with db() as con:
        for item in payload.entries:
            username=str(item.get('username','')).strip()
            if not username: continue
            con.execute('INSERT INTO users(username,display_name,email,password_hash,source,external_id,role,language,communication_language,email_enabled,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(username) DO UPDATE SET display_name=excluded.display_name,email=excluded.email,source=excluded.source,external_id=excluded.external_id,updated_at=excluded.updated_at', (username,str(item.get('display_name','')),str(item.get('email','')),'','ldap',str(item.get('dn','')),role,APP_LANGUAGE_DEFAULT,COMMUNICATION_LANGUAGE_DEFAULT,1,1,now,now)); imported+=1
    return {'imported':imported}

@app.post('/api/admin/oidc/test')
async def test_oidc_configuration(authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization); cfg=runtime_config()
    if not cfg['oidc_discovery_url']: raise HTTPException(400,'OIDC discovery URL is required')
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client: r=await client.get(cfg['oidc_discovery_url']); r.raise_for_status(); data=r.json()
        log_event('oidc','success','OIDC discovery test successful', str(data.get('issuer') or ''))
        return {'ok':True,'issuer':data.get('issuer'),'authorization_endpoint':data.get('authorization_endpoint'),'token_endpoint':data.get('token_endpoint')}
    except Exception as exc:
        log_event('oidc','error','OIDC discovery test failed', f'{type(exc).__name__}: {exc}')
        raise HTTPException(502,str(exc))

@app.get('/api/admin/users')
async def list_users(authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    with db() as con: rows=con.execute('SELECT * FROM users ORDER BY role DESC, username').fetchall()
    return {'users':[serialize_user(r) for r in rows]}

@app.post('/api/admin/users')
async def create_user(payload: UserCreateRequest, authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    if not re.fullmatch(r'[A-Za-z0-9._@-]{2,80}',payload.username): raise HTTPException(400,'Invalid username')
    if len(payload.password)<8: raise HTTPException(400,'Password must contain at least 8 characters')
    now=now_local().isoformat(timespec='seconds')
    try:
        with db() as con:
            cur=con.execute('INSERT INTO users(username,display_name,email,password_hash,source,role,language,communication_language,email_enabled,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(payload.username,payload.display_name,payload.email,hash_password(payload.password),'local',payload.role if payload.role in {'user','admin'} else 'user',payload.language,payload.communication_language,int(payload.email_enabled),1,now,now)); uid=cur.lastrowid; row=con.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
        return serialize_user(row)
    except sqlite3.IntegrityError: raise HTTPException(409,'Username already exists')

@app.put('/api/admin/users/{user_id}')
async def update_user(user_id:int,payload:UserUpdateRequest,authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization); now=now_local().isoformat(timespec='seconds')
    with db() as con:
        row=con.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone()
        if not row: raise HTTPException(404,'User not found')
        if row['role']=='admin' and (payload.role!='admin' or not payload.active):
            admins=con.execute("SELECT COUNT(*) AS c FROM users WHERE role='admin' AND active=1").fetchone()['c']
            if admins<=1: raise HTTPException(400,'The last active administrator cannot be disabled or demoted')
        password_hash=hash_password(payload.password) if payload.password else row['password_hash']
        con.execute('UPDATE users SET display_name=?,email=?,password_hash=?,role=?,language=?,communication_language=?,email_enabled=?,active=?,updated_at=? WHERE id=?',(payload.display_name,payload.email,password_hash,payload.role if payload.role in {'user','admin'} else 'user',payload.language,payload.communication_language,int(payload.email_enabled),int(payload.active),now,user_id)); updated=con.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone()
    return serialize_user(updated)

@app.get('/api/auth/providers')
async def auth_providers():
    cfg=runtime_config()
    return {'local':True,'oidc':{'enabled':bool(cfg['oidc_enabled'] and cfg['oidc_discovery_url'] and cfg['oidc_client_id']),'login_url':'/api/auth/oidc/login'}}

@app.get('/api/auth/oidc/login')
async def oidc_login():
    cfg=runtime_config()
    if not cfg['oidc_enabled']: raise HTTPException(404,'OIDC authentication is disabled')
    if not cfg['oidc_discovery_url'] or not cfg['oidc_client_id']: raise HTTPException(503,'OIDC configuration is incomplete')
    async with httpx.AsyncClient(timeout=10,follow_redirects=True) as client:
        discovery=(await client.get(cfg['oidc_discovery_url'])).json()
    authorization_endpoint=discovery.get('authorization_endpoint')
    if not authorization_endpoint: raise HTTPException(502,'OIDC authorization endpoint is missing')
    state=secrets.token_urlsafe(32); oidc_states[state]={'expires':time.time()+600}
    redirect_uri=(app_public_url() or 'http://localhost:8080')+'/api/auth/oidc/callback'
    params={'client_id':cfg['oidc_client_id'],'response_type':'code','scope':cfg['oidc_scopes'],'redirect_uri':redirect_uri,'state':state}
    return RedirectResponse(authorization_endpoint+'?'+urlencode(params),status_code=302)

@app.get('/api/auth/oidc/callback')
async def oidc_callback(code:str|None=None,state:str|None=None,error:str|None=None,error_description:str|None=None):
    if error: return RedirectResponse('/#oidc_error='+quote(error_description or error),status_code=302)
    state_data=oidc_states.pop(state or '',None)
    if not code or not state_data or state_data['expires']<time.time():
        return RedirectResponse('/#oidc_error='+quote('Invalid or expired OIDC state'),status_code=302)
    cfg=runtime_config(); redirect_uri=(app_public_url() or 'http://localhost:8080')+'/api/auth/oidc/callback'
    try:
        async with httpx.AsyncClient(timeout=15,follow_redirects=True) as client:
            discovery_response=await client.get(cfg['oidc_discovery_url']); discovery_response.raise_for_status(); discovery=discovery_response.json()
            token_response=await client.post(discovery['token_endpoint'],data={'grant_type':'authorization_code','code':code,'redirect_uri':redirect_uri,'client_id':cfg['oidc_client_id'],'client_secret':cfg['oidc_client_secret']})
            token_response.raise_for_status(); tokens=token_response.json(); access_token=tokens.get('access_token')
            if not access_token: raise RuntimeError('OIDC provider did not return an access token')
            userinfo_endpoint=discovery.get('userinfo_endpoint')
            if not userinfo_endpoint: raise RuntimeError('OIDC userinfo endpoint is missing')
            userinfo_response=await client.get(userinfo_endpoint,headers={'Authorization':'Bearer '+access_token}); userinfo_response.raise_for_status(); claims=userinfo_response.json()
        username=str(claims.get(cfg['oidc_username_claim']) or claims.get('preferred_username') or claims.get('sub') or '').strip()
        email=str(claims.get(cfg['oidc_email_claim']) or claims.get('email') or '').strip()
        subject=str(claims.get('sub') or username).strip(); display_name=str(claims.get('name') or username).strip()
        groups=claims.get(cfg['oidc_groups_claim'],[]) or []
        if isinstance(groups,str): groups=[groups]
        if not username: raise RuntimeError('OIDC username claim is missing')
        if cfg['oidc_allowed_group'] and cfg['oidc_allowed_group'] not in groups: raise RuntimeError('User is not a member of the allowed OIDC group')
        role='admin' if cfg['oidc_admin_group'] and cfg['oidc_admin_group'] in groups else 'user'
        now=now_local().isoformat(timespec='seconds')
        with db() as con:
            row=con.execute("SELECT * FROM users WHERE source='oidc' AND external_id=?",(subject,)).fetchone()
            if not row: row=con.execute('SELECT * FROM users WHERE username=? COLLATE NOCASE',(username,)).fetchone()
            if not row:
                if not cfg['oidc_auto_create_users']: raise RuntimeError('Automatic OIDC user creation is disabled')
                con.execute('INSERT INTO users(username,display_name,email,password_hash,source,external_id,role,language,communication_language,email_enabled,active,last_login,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(username,display_name,email,'','oidc',subject,role,APP_LANGUAGE_DEFAULT,COMMUNICATION_LANGUAGE_DEFAULT,1,1,now,now,now))
                row=con.execute('SELECT * FROM users WHERE username=? COLLATE NOCASE',(username,)).fetchone()
            else:
                con.execute('UPDATE users SET display_name=?,email=?,external_id=?,role=?,last_login=?,updated_at=? WHERE id=?',(display_name,email,subject,role,now,now,row['id']))
                row=con.execute('SELECT * FROM users WHERE id=?',(row['id'],)).fetchone()
        token,expires=create_user_session(dict(row))
        return RedirectResponse('/#oidc_token='+quote(token),status_code=302)
    except Exception as exc:
        return RedirectResponse('/#oidc_error='+quote(str(exc)),status_code=302)

@app.post('/api/auth/login')
async def local_login(payload:LocalLoginRequest):
    with db() as con: row=con.execute('SELECT * FROM users WHERE username=? COLLATE NOCASE AND active=1',(payload.username,)).fetchone()
    cfg=runtime_config()
    if not row and cfg.get('ldap_enabled') and cfg.get('ldap_jit_provisioning'):
        try:
            profile=ldap_authenticate_and_profile(payload.username,payload.password,cfg)
            if profile:
                now=now_local().isoformat(timespec='seconds')
                with db() as con:
                    con.execute('INSERT INTO users(username,display_name,email,password_hash,source,external_id,role,language,communication_language,email_enabled,active,last_login,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(profile['username'],profile['display_name'],profile['email'],'','ldap',profile['dn'],profile['role'],APP_LANGUAGE_DEFAULT,COMMUNICATION_LANGUAGE_DEFAULT,1,1,now,now,now))
                    row=con.execute('SELECT * FROM users WHERE username=? COLLATE NOCASE',(profile['username'],)).fetchone()
                log_event('ldap','success','LDAP JIT account created',f"user={profile['username']}; matched_groups={','.join(profile.get('matched_groups', [])) or '-'}; role={profile['role']}")
                log_event('authentication','success','Login successful',f"user={profile['username']}; source=ldap; role={profile['role']}")
                token,expires=create_user_session(dict(row)); log_event('authentication','success','Login successful',f'user={row["username"]}; source={row["source"]}; role={row["role"]}'); return {'token':token,'expires_at':expires,'user':serialize_user(row)}
        except Exception as exc:
            log_event('ldap','error','LDAP JIT login failed',f'{type(exc).__name__}: {exc}')
    if not row:
        log_event('authentication','warning','Login failed',f'user={payload.username}; reason=unknown_user_or_invalid_credentials')
        raise HTTPException(401,'Invalid username or password')
    authenticated = False
    if row['source']=='local':
        authenticated = verify_password(payload.password,row['password_hash'])
    elif row['source']=='ldap':
        cfg=runtime_config()
        if cfg['ldap_enabled']:
            try:
                profile=ldap_authenticate_and_profile(payload.username,payload.password,cfg)
                authenticated=bool(profile)
                if profile:
                    now=now_local().isoformat(timespec='seconds')
                    with db() as con:
                        con.execute('UPDATE users SET display_name=?,email=?,external_id=?,role=?,updated_at=? WHERE id=?',(profile['display_name'],profile['email'],profile['dn'],profile['role'],now,row['id']))
                        row=con.execute('SELECT * FROM users WHERE id=?',(row['id'],)).fetchone()
                    log_event('ldap','success','LDAP account synchronized at login',f"user={profile['username']}; matched_groups={','.join(profile.get('matched_groups', [])) or '-'}; role={profile['role']}")
            except Exception as exc:
                log_event('ldap','error','LDAP login failed',f'{type(exc).__name__}: {exc}')
                authenticated=False
    if not authenticated:
        log_event('authentication','warning','Login failed',f'user={payload.username}; source={row["source"]}; reason=invalid_credentials')
        raise HTTPException(401,'Invalid username or password')
    now=now_local().isoformat(timespec='seconds')
    with db() as con: con.execute('UPDATE users SET last_login=?,updated_at=? WHERE id=?',(now,now,row['id'])); row=con.execute('SELECT * FROM users WHERE id=?',(row['id'],)).fetchone()
    token,expires=create_user_session(dict(row)); return {'token':token,'expires_at':expires,'user':serialize_user(row)}

@app.get('/api/auth/me')
async def auth_me(authorization: str | None = Header(default=None)):
    return serialize_user(current_user(authorization))

@app.put('/api/profile')
async def update_profile(payload:ProfileUpdateRequest, authorization: str | None = Header(default=None)):
    user=current_user(authorization); now=now_local().isoformat(timespec='seconds')
    with db() as con:
        row=con.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone(); password_hash=hash_password(payload.password) if payload.password and row['source']=='local' else row['password_hash']
        con.execute('UPDATE users SET language=?,communication_language=?,email_enabled=?,password_hash=?,updated_at=? WHERE id=?',(payload.language,payload.communication_language,int(payload.email_enabled),password_hash,now,user['id'])); updated=con.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone()
    return serialize_user(updated)

@app.get('/api/reports/summary')
async def reports_summary(days:int=Query(30,ge=1,le=365),authorization: str | None = Header(default=None)):
    require_admin_or_user_admin(authorization)
    issues=cache.get('issues',[])
    today=now_local().date()
    past_start=today-timedelta(days=days-1)
    future_end=today+timedelta(days=days-1)

    completed_daily={(past_start+timedelta(days=n)).isoformat():0 for n in range(days)}
    scheduled_daily={(today+timedelta(days=n)).isoformat():0 for n in range(days)}

    past_issues=[]
    upcoming=[]
    report_scope=[]
    by_env={}
    by_priority={}
    by_status={}
    scheduled_count=0

    for i in issues:
        date_value=i.get('start_date') or ''
        try:
            issue_date=datetime.fromisoformat(date_value).date()
        except Exception:
            continue

        # Past series: releases occurring during the selected past period.
        if past_start <= issue_date <= today:
            past_issues.append(i)
            completed_daily[issue_date.isoformat()]+=1

        # Future series: releases scheduled during the selected future period.
        if today <= issue_date <= future_end:
            upcoming.append(i)
            scheduled_daily[issue_date.isoformat()]+=1

        # Breakdown charts use the complete selected window:
        # selected past period + today + selected future period.
        if past_start <= issue_date <= future_end:
            report_scope.append(i)

            env=(i.get('environment') or 'Unspecified').strip()
            priority=(i.get('priority') or 'Normal').strip()
            status=(i.get('status') or 'Unspecified').strip()

            by_env[env]=by_env.get(env,0)+1
            by_priority[priority]=by_priority.get(priority,0)+1
            by_status[status]=by_status.get(status,0)+1

            if i.get('start_time'):
                scheduled_count+=1

    releases=len(report_scope)
    schedule_quality=round((scheduled_count/releases)*100,1) if releases else 0
    cutoff=past_start.isoformat()

    with db() as con:
        smtp_ok=con.execute("SELECT COUNT(*) AS c FROM notifications WHERE sent_at>=? AND status='sent'",(cutoff,)).fetchone()['c']
        smtp_ko=con.execute("SELECT COUNT(*) AS c FROM notifications WHERE sent_at>=? AND status='error'",(cutoff,)).fetchone()['c']

    return {
        'days':days,
        'releases':releases,
        'past_releases':len(past_issues),
        'upcoming_releases':len(upcoming),
        'without_time':sum(1 for i in report_scope if not i.get('start_time')),
        'urgent':sum(1 for i in report_scope if (i.get('priority_level') or 1)>=3),
        'schedule_quality':schedule_quality,
        'by_environment':by_env,
        'by_priority':by_priority,
        'by_status':by_status,
        'timeline_completed':[{'date':date,'count':count} for date,count in completed_daily.items()],
        'timeline_scheduled':[{'date':date,'count':count} for date,count in scheduled_daily.items()],
        'timeline':[{'date':date,'count':count} for date,count in completed_daily.items()],
        'communications_sent':smtp_ok,
        'communications_errors':smtp_ko
    }
