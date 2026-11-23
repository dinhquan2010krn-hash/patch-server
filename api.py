"""Public API compatible with the ThreeOneOSFive / XAVION client."""
import os
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file, abort

from config import config
from database import db
from license_service import (
    activate,
    issue_token,
    patch_config,
    verify_token,
)

api = Blueprint("api", __name__)


def _json():
    return request.get_json(silent=True) or {}


@api.post("/api/v1/activate")
def api_activate():
    body = _json()
    ok, message, data = activate(
        body.get("key"),
        body.get("deviceId") or body.get("device_id"),
        body.get("bundleId") or body.get("bundle_id", ""),
        body.get("appVersion") or body.get("app_version", ""),
    )
    return jsonify({"success": ok, "message": message, "data": data}), (200 if ok else 400)


@api.post("/api/v1/get_token")
@api.post("/api/v1/download/token")
def api_get_token():
    body = _json()
    ok, message, data = issue_token(
        body.get("key"), body.get("deviceId") or body.get("device_id")
    )
    status = 200 if ok else 400
    if ok:
        return jsonify(data), status
    return jsonify({"success": False, "message": message}), status


@api.get("/api/v1/content/config")
def api_config():
    return jsonify(patch_config(request.host_url.rstrip("/")))


@api.get("/api/v1/version")
def api_version():
    return jsonify({
        "force_update": False,
        "latest_version": config.LATEST_VERSION,
        "update_url": "",
    })


@api.get("/health")
def api_health():
    return jsonify({"github_sync": False, "ok": True, "service": "Local Patch Key Server"})


@api.get("/api/v1/download/<filename>")
def api_download_compat(filename):
    """Compatibility route used by fileURL values in config (token in query/header)."""
    token = request.args.get("token") or request.args.get("access_token")
    uid = request.args.get("uid") or request.args.get("device_id")
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        token = token or header[7:].strip()
    if not token or not uid:
        abort(404)
    return _serve_patch(filename, uid, token)


@api.get("/api/v1/download/file/<filename>/<uid>/<token>")
def api_download_file(filename, uid, token):
    """Exact route used by the app: /api/v1/download/file/<file>/<uid>/<token>."""
    if not verify_token(token, uid):
        return jsonify({"message": "Token khong hop le hoac da bi thu hoi", "success": False}), 401
    return _serve_patch(filename, uid, token)


def _serve_patch(filename, uid, token):
    # Validate filename against the database (prevents path traversal).
    with db() as conn:
        patch = conn.execute(
            "SELECT * FROM patches WHERE filename = ? AND enabled = 1", (filename,)
        ).fetchone()
    if not patch:
        abort(404)
    path = Path(config.PATCH_DIR) / patch["stored_name"]
    if not path.is_file():
        abort(404)
    return send_file(
        str(path),
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=patch["filename"],
        conditional=True,
    )
