#!/usr/bin/env python3
r"""Import .3105 patch files from a local folder into the server database.

Usage:
    python tools/import_patches.py "D:\Users\ANH MY\Downloads\XAVION VN PATCH"
"""
import argparse
import secrets
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import config
from database import db, init_db
import json
import urllib.request

GAME_DIRS = {
    "ffth": "free-fire",
    "ffm": "free-fire-max",
    "ffvn": "free-fire-vn",
}

# Fallback category map for known items; config.json from the real server is
# consulted first when reachable.
AIM_PREFIXES = ("aim", "bung", "co-anten", "lisdex")


def load_remote_meta():
    try:
        with urllib.request.urlopen(
            "https://mduyk-key-server.onrender.com/api/v1/content/config", timeout=10
        ) as r:
            cfg = json.loads(r.read().decode("utf-8"))
        meta = {}
        for g in cfg.get("games", []):
            for it in g.get("items", []):
                meta[it["id"]] = {
                    "game_id": g["id"],
                    "category": it.get("category", "mod"),
                    "subtitle": it.get("subtitle", ""),
                    "password": it.get("packagePassword", ""),
                }
        return meta
    except Exception as exc:
        print("NOTE: khong tai duoc config cu, dung fallback category:", exc)
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="folder containing ffth/ffm/ffvn subfolders")
    args = ap.parse_args()

    src_root = Path(args.folder)
    if not src_root.is_dir():
        print("ERROR: not a folder:", src_root, file=sys.stderr)
        return 1

    init_db()
    remote = load_remote_meta()
    patch_dir = Path(config.PATCH_DIR)
    patch_dir.mkdir(parents=True, exist_ok=True)

    imported = 0
    skipped = 0
    with db() as conn:
        for sub, game_id in GAME_DIRS.items():
            folder = src_root / sub
            if not folder.is_dir():
                continue
            for file in sorted(folder.glob("*.3105")):
                item_id = file.stem
                meta = remote.get(item_id, {})
                category = meta.get("category") or (
                    "aim" if item_id.lower().startswith(AIM_PREFIXES) else "mod"
                )
                subtitle = meta.get("subtitle", "")
                password = meta.get("password", "")
                real_game = meta.get("game_id", game_id)

                stored = secrets.token_hex(8) + ".3105"
                dest = patch_dir / stored
                shutil.copy2(str(file), str(dest))

                conn.execute(
                    "INSERT OR REPLACE INTO patches "
                    "(filename, stored_name, game_id, item_id, name, category, subtitle, "
                    " package_password, enabled, size, uploaded_at) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?, ?, 1, ?, datetime('now'))",
                    (file.name, stored, real_game, item_id, item_id, category,
                     subtitle, password, dest.stat().st_size),
                )
                print(f"  + {real_game}/{category:4} {file.name} ({dest.stat().st_size} bytes)")
                imported += 1

        # remove stale demo/test entries if any
        conn.execute("DELETE FROM patches WHERE filename LIKE 'TEST_%'")
        skipped = conn.execute("SELECT COUNT(*) AS n FROM patches").fetchone()["n"] - imported

    print()
    print(f"Imported: {imported}, existing/other rows kept: {skipped}")
    print(f"Patch dir: {patch_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
