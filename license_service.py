"""License validation, activation and access-token logic.

A license is "lifetime" when duration_days < 0 (e.g. -1).
In that case expires_at stays NULL and no expiry check is performed.
"""
import secrets
from datetime import datetime, timedelta, timezone

from config import config
from database import db, now_iso, setting_get

LIFETIME_SENTINEL = -1


def _as_int(value, default=0):
    """SQLite may return TEXT/NULL for an INTEGER column - always coerce safely."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_dt(value):
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _is_lifetime(row):
    return _as_int(row["duration_days"], 0) < 0 or not row["expires_at"]


def license_status(license_key):
    """Return a dict with license information, or None if not found."""
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM licenses WHERE license_key = ?", (license_key,)
        ).fetchone()
        if not row:
            return None
        devices = conn.execute(
            "SELECT device_id, activated_at FROM devices WHERE license_id = ?",
            (row["id"],),
        ).fetchall()

    lifetime = _is_lifetime(row)
    expires = _parse_dt(row["expires_at"])
    remaining = (expires - datetime.now(timezone.utc)).days if expires else 0
    return {
        "id": row["id"],
        "licenseKey": row["license_key"],
        "status": row["status"],
        "plan": row["plan"],
        "note": row["note"],
        "maxDevices": _as_int(row["max_devices"], 1),
        "durationDays": _as_int(row["duration_days"], 0),
        "isLifetime": lifetime,
        "activatedAt": row["activated_at"],
        "expiresAt": None if lifetime else row["expires_at"],
        "remainingDays": -1 if lifetime else max(remaining, 0),
        "devices": [dict(d) for d in devices],
    }


def activate(key, device_id, bundle_id="", app_version=""):
    """Activate a license on a device. Returns (ok, message, data)."""
    if not key or not device_id:
        return False, "Thieu key hoac thiet bi", None

    with db() as conn:
        row = conn.execute(
            "SELECT * FROM licenses WHERE license_key = ?", (key,)
        ).fetchone()
        if not row:
            return False, "License key khong hop le", None
        if row["status"] != "active":
            return False, "License key da bi vo hieu hoa", None

        lifetime = _is_lifetime(row)
        if not lifetime:
            expires = _parse_dt(row["expires_at"])
            if expires and expires < datetime.now(timezone.utc):
                return False, "License key da het han", None

        max_devices = _as_int(row["max_devices"], 1)
        device = conn.execute(
            "SELECT * FROM devices WHERE license_id = ? AND device_id = ?",
            (row["id"], device_id),
        ).fetchone()
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM devices WHERE license_id = ?", (row["id"],)
        ).fetchone()["n"]

        if not device and count >= max_devices:
            return False, "Key da dat gioi han %d thiet bi" % max_devices, None

        activated_at = row["activated_at"] or now_iso()
        if not row["activated_at"]:
            if lifetime:
                expires_at = None
            else:
                days = _as_int(row["duration_days"], config.DEFAULT_LICENSE_DAYS)
                expires_at = (
                    datetime.now(timezone.utc) + timedelta(days=days)
                ).isoformat(timespec="seconds")
            conn.execute(
                "UPDATE licenses SET activated_at = ?, expires_at = ? WHERE id = ?",
                (activated_at, expires_at, row["id"]),
            )
        else:
            expires_at = None if lifetime else row["expires_at"]

        if not device:
            conn.execute(
                "INSERT INTO devices(license_id, device_id, bundle_id, app_version, activated_at) "
                "VALUES(?, ?, ?, ?, ?)",
                (row["id"], device_id, bundle_id, app_version, now_iso()),
            )
        else:
            conn.execute(
                "UPDATE devices SET bundle_id = ?, app_version = ? WHERE id = ?",
                (bundle_id, app_version, device["id"]),
            )

    info = license_status(key)
    data = {
        "activatedAt": info["activatedAt"],
        "deviceId": device_id,
        "expiresAt": info["expiresAt"],
        "hwid": device_id,
        "key": key,
        "licenseKey": key,
        "maxDevices": info["maxDevices"],
        "plan": info["plan"],
        "remainingDays": info["remainingDays"],
        "status": info["status"],
        "isLifetime": info["isLifetime"],
    }
    return True, "OK", data


def issue_token(key, device_id):
    """Issue an access token for an activated device. Returns (ok, message, data)."""
    if not key or not device_id:
        return False, "Thieu key hoac device_id", None

    info = license_status(key)
    if not info:
        return False, "License key khong hop le", None
    if info["status"] != "active":
        return False, "License key da bi vo hieu hoa", None
    if not info["isLifetime"]:
        expires = _parse_dt(info["expiresAt"])
        if expires and expires < datetime.now(timezone.utc):
            return False, "License key da het han", None
    if device_id not in [d["device_id"] for d in info["devices"]]:
        return False, "Thiet bi chua duoc kich hoat bang license nay", None

    ttl = config.TOKEN_TTL_SECONDS
    token = secrets.token_urlsafe(32)
    expires_at = int(datetime.now(timezone.utc).timestamp()) + ttl
    with db() as conn:
        conn.execute(
            "INSERT INTO tokens(token, license_id, device_id, expires_at, created_at) "
            "VALUES(?, ?, ?, ?, ?)",
            (token, info["id"], device_id, expires_at, now_iso()),
        )
    return True, "OK", {
        "success": True,
        "token": token,
        "uid": device_id,
        "expires_at": expires_at,
        "expires_in": ttl,
    }


def verify_token(token, device_id=None):
    """Return the token row if valid, else None."""
    if not token:
        return None
    with db() as conn:
        row = conn.execute("SELECT * FROM tokens WHERE token = ?", (token,)).fetchone()
    if not row or row["revoked"]:
        return None
    if _as_int(row["expires_at"], 0) < int(datetime.now(timezone.utc).timestamp()):
        return None
    if device_id is not None and row["device_id"] != device_id:
        return None
    return row


def create_license(key=None, days=None, max_devices=None, plan="", note="", lifetime=False):
    """Create a license. days < 0 or lifetime=True means permanent (no expiry)."""
    key = key or ("MDUYK-" + secrets.token_hex(8).upper() + "-" + secrets.token_hex(4).upper())
    if lifetime:
        days = LIFETIME_SENTINEL
    else:
        days = _as_int(days, config.DEFAULT_LICENSE_DAYS)
    max_devices = _as_int(max_devices, config.DEFAULT_MAX_DEVICES)
    with db() as conn:
        conn.execute(
            "INSERT INTO licenses(license_key, note, plan, max_devices, duration_days, created_at) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (key, note, plan, max_devices, days, now_iso()),
        )
    return key


def make_lifetime(key):
    """Turn an existing license into a lifetime one and reset its activations."""
    with db() as conn:
        row = conn.execute("SELECT id FROM licenses WHERE license_key = ?", (key,)).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE licenses SET duration_days = ?, expires_at = NULL, "
            "activated_at = NULL, status = 'active' WHERE id = ?",
            (LIFETIME_SENTINEL, row["id"]),
        )
        conn.execute("DELETE FROM devices WHERE license_id = ?", (row["id"],))
        conn.execute("UPDATE tokens SET revoked = 1 WHERE license_id = ?", (row["id"],))
    return True


def revoke_license(key):
    with db() as conn:
        conn.execute("UPDATE licenses SET status = 'revoked' WHERE license_key = ?", (key,))
        conn.execute(
            "UPDATE tokens SET revoked = 1 WHERE license_id IN "
            "(SELECT id FROM licenses WHERE license_key = ?)",
            (key,),
        )


def patch_config(base_url=""):
    """Build the JSON returned by /api/v1/content/config.

    base_url (e.g. https://your-app.onrender.com) makes fileURL absolute,
    matching the behaviour of the original server.
    """
    with db() as conn:
        patches = conn.execute(
            "SELECT * FROM patches WHERE enabled = 1 ORDER BY game_id, category, id"
        ).fetchall()
        cfg_rows = conn.execute("SELECT key, value FROM settings").fetchall()
    settings = {r["key"]: r["value"] for r in cfg_rows}

    games = {}
    for p in patches:
        g = games.setdefault(p["game_id"], {
            "id": p["game_id"],
            "name": p["game_id"].replace("-", " ").title(),
            "bundleID": "",
            "iconURL": "",
            "items": [],
        })
        g["items"].append({
            "id": p["item_id"],
            "name": p["name"],
            "category": p["category"],
            "subtitle": p["subtitle"],
            "enabled": True,
            "order": len(g["items"]) + 1,
            "fileURL": (base_url.rstrip("/") if base_url else "")
                       + "/api/v1/download/" + p["filename"],
            "packagePassword": p["package_password"],
        })

    return {
        "brandTitle": settings.get("brand_title", config.BRAND_TITLE),
        "brandSubtitle": settings.get("brand_subtitle", config.BRAND_SUBTITLE),
        "latestVersion": settings.get("latest_version", config.LATEST_VERSION),
        "minimumVersion": settings.get("minimum_version", config.MINIMUM_VERSION),
        "forceUpdate": settings.get("force_update", str(config.FORCE_UPDATE)).lower() == "true",
        "maintenanceEnabled": settings.get(
            "maintenance_enabled", str(config.MAINTENANCE_ENABLED)
        ).lower() == "true",
        "maintenanceMessage": settings.get("maintenance_message", config.MAINTENANCE_MESSAGE),
        "noticeTitle": settings.get("notice_title", config.NOTICE_TITLE),
        "noticeMessage": settings.get("notice_message", config.NOTICE_MESSAGE),
        "pageVisibility": {
            "cleaner": True, "files": True, "games": True,
            "home": True, "patches": True, "wallpaper": True,
        },
        "games": list(games.values()),
    }
