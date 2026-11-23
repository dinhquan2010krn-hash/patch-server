"""Admin UI: login, licenses, patch upload/management, content settings."""
import os
import re
import secrets
from pathlib import Path

from flask import (
    Blueprint, abort, flash, redirect, render_template, request,
    send_from_directory, session, url_for,
)
from werkzeug.utils import secure_filename

from config import config
from database import db, setting_get, setting_set
from license_service import create_license, license_status, patch_config, revoke_license

admin = Blueprint("admin", __name__)

ALLOWED_EXTENSIONS = {".3105"}


def csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return session["_csrf_token"]


def check_csrf():
    if request.method == "POST":
        sent = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")
        if not sent or sent != session.get("_csrf_token"):
            abort(400, "Invalid CSRF token")


@admin.before_request
def _require_login():
    if request.endpoint in ("admin.login", "admin.static_file"):
        return
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.login"))
    check_csrf()


@admin.app_context_processor
def _inject():
    return {"csrf_token": csrf_token}


@admin.route("/admin/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        check_csrf()
        if request.form.get("key", "") == config.ADMIN_KEY:
            session.clear()
            session["admin_logged_in"] = True
            session["_csrf_token"] = secrets.token_urlsafe(32)
            flash("Dang nhap thanh cong.")
            return redirect(url_for("admin.dashboard"))
        error = "Admin access key khong dung."
    return render_template("admin_login.html", error=error)


@admin.route("/admin/logout", methods=["POST"])
def logout():
    check_csrf()
    session.clear()
    return redirect(url_for("admin.login"))


@admin.route("/admin")
def dashboard():
    with db() as conn:
        stats = {
            "licenses": conn.execute("SELECT COUNT(*) AS n FROM licenses").fetchone()["n"],
            "active_licenses": conn.execute(
                "SELECT COUNT(*) AS n FROM licenses WHERE status = 'active'"
            ).fetchone()["n"],
            "devices": conn.execute("SELECT COUNT(*) AS n FROM devices").fetchone()["n"],
            "tokens": conn.execute("SELECT COUNT(*) AS n FROM tokens").fetchone()["n"],
            "patches": conn.execute("SELECT COUNT(*) AS n FROM patches").fetchone()["n"],
        }
        recent = conn.execute(
            "SELECT * FROM licenses ORDER BY id DESC LIMIT 8"
        ).fetchall()
    return render_template("admin_dashboard.html", stats=stats, recent=recent)


# ---------------------------------------------------------------- licenses
@admin.route("/admin/licenses")
def licenses():
    with db() as conn:
        rows = conn.execute("SELECT * FROM licenses ORDER BY id DESC").fetchall()
        item = license_status(rows[0]["license_key"]) if rows else None
    return render_template("admin_licenses.html", rows=rows)


@admin.route("/admin/licenses/create", methods=["POST"])
def license_create():
    check_csrf()
    key = request.form.get("license_key", "").strip() or None
    try:
        created = create_license(
            key=key,
            days=request.form.get("duration_days"),
            max_devices=request.form.get("max_devices"),
            plan=request.form.get("plan", ""),
            note=request.form.get("note", ""),
        )
        flash("Da tao license: " + created)
    except Exception as exc:
        flash("Loi: " + str(exc))
    return redirect(url_for("admin.licenses"))


@admin.route("/admin/licenses/revoke", methods=["POST"])
def license_revoke():
    check_csrf()
    revoke_license(request.form.get("license_key", ""))
    flash("Da vo hieu hoa license.")
    return redirect(url_for("admin.licenses"))


# ------------------------------------------------------------------ patches
@admin.route("/admin/patches")
def patches():
    with db() as conn:
        rows = conn.execute("SELECT * FROM patches ORDER BY game_id, category, id").fetchall()
    return render_template("admin_patches.html", rows=rows)


@admin.route("/admin/patches/upload", methods=["POST"])
def patch_upload():
    check_csrf()
    files = request.files.getlist("files")
    game_id = request.form.get("game_id", "free-fire").strip() or "free-fire"
    category = request.form.get("category", "mod").strip() or "mod"
    password = request.form.get("package_password", "").strip()
    count = 0
    for file in files:
        if not file or not file.filename:
            continue
        filename = secure_filename(file.filename)
        if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
            flash("Bo qua (khong phai .3105): " + filename)
            continue
        stored_name = secrets.token_hex(8) + ".3105"
        dest = Path(config.PATCH_DIR) / stored_name
        file.save(str(dest))
        item_id = Path(filename).stem
        with db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO patches"
                "(filename, stored_name, game_id, item_id, name, category, subtitle, "
                " package_password, enabled, size, uploaded_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, 1, ?, datetime('now'))",
                (filename, stored_name, game_id, item_id, item_id, category, "",
                 password, dest.stat().st_size),
            )
        count += 1
    flash("Da upload %d file patch." % count)
    return redirect(url_for("admin.patches"))


@admin.route("/admin/patches/toggle", methods=["POST"])
def patch_toggle():
    check_csrf()
    with db() as conn:
        row = conn.execute(
            "SELECT enabled FROM patches WHERE id = ?", (request.form.get("id"),)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE patches SET enabled = ? WHERE id = ?",
                (0 if row["enabled"] else 1, request.form.get("id")),
            )
    return redirect(url_for("admin.patches"))


@admin.route("/admin/patches/delete", methods=["POST"])
def patch_delete():
    check_csrf()
    with db() as conn:
        row = conn.execute(
            "SELECT stored_name FROM patches WHERE id = ?", (request.form.get("id"),)
        ).fetchone()
        if row:
            path = Path(config.PATCH_DIR) / row["stored_name"]
            if path.is_file():
                path.unlink()
            conn.execute("DELETE FROM patches WHERE id = ?", (request.form.get("id"),))
    flash("Da xoa patch.")
    return redirect(url_for("admin.patches"))


@admin.route("/admin/patches/download/<int:patch_id>")
def patch_download(patch_id):
    with db() as conn:
        row = conn.execute("SELECT * FROM patches WHERE id = ?", (patch_id,)).fetchone()
    if not row:
        abort(404)
    return send_from_directory(
        config.PATCH_DIR, row["stored_name"], as_attachment=True,
        download_name=row["filename"],
    )


# ------------------------------------------------------------------ config
CONTENT_KEYS = [
    ("brand_title", "Brand title"),
    ("brand_subtitle", "Brand subtitle"),
    ("latest_version", "Latest version"),
    ("minimum_version", "Minimum version"),
    ("notice_title", "Notice title"),
    ("notice_message", "Notice message"),
    ("maintenance_message", "Maintenance message"),
    ("force_update", "Force update (true/false)"),
    ("maintenance_enabled", "Maintenance (true/false)"),
]


@admin.route("/admin/config", methods=["GET", "POST"])
def config_editor():
    if request.method == "POST":
        check_csrf()
        for key, _ in CONTENT_KEYS:
            value = request.form.get(key, "")
            setting_set(key, value)
        flash("Da luu cau hinh.")
        return redirect(url_for("admin.config_editor"))
    values = {key: setting_get(key, getattr(config, key.upper(), "")) for key, _ in CONTENT_KEYS}
    return render_template("admin_config.html", fields=CONTENT_KEYS, values=values)
