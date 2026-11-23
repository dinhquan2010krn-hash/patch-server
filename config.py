"""Configuration for the local ThreeOneOSFive-compatible key & patch server."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
PATCH_DIR = INSTANCE_DIR / "patches"
DB_PATH = INSTANCE_DIR / "server.db"


class Config:
    # Change this before exposing the server to anyone.
    SECRET_KEY = os.environ.get("SERVER_SECRET_KEY", "dev-only-change-me-please")
    ADMIN_KEY = os.environ.get("ADMIN_KEY", "admin123")

    DATABASE = str(DB_PATH)
    PATCH_DIR = str(PATCH_DIR)

    TOKEN_TTL_SECONDS = 10800  # 3 hours, matches the original server
    DEFAULT_LICENSE_DAYS = 30
    DEFAULT_MAX_DEVICES = 1

    # Content served by GET /api/v1/content/config ; editable in the admin UI.
    BRAND_TITLE = "MDUYK LOCAL"
    BRAND_SUBTITLE = "Local Patch Server"
    LATEST_VERSION = "1.1.2"
    MINIMUM_VERSION = "1.1.2"
    FORCE_UPDATE = False
    MAINTENANCE_ENABLED = False
    MAINTENANCE_MESSAGE = "He thong dang bao tri. Vui long quay lai sau!"
    NOTICE_TITLE = "Thong bao"
    NOTICE_MESSAGE = "Chao mung ban den voi may chu patch local."


config = Config()
INSTANCE_DIR.mkdir(exist_ok=True)
PATCH_DIR.mkdir(exist_ok=True)
