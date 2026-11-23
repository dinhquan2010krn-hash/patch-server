"""Create starter data (a demo license). Run: python seed.py"""
from database import init_db
from license_service import create_license

if __name__ == "__main__":
    init_db()
    key = create_license(
        key="MDUYK-DEMO000000000000-DEMO0001",
        days=30,
        max_devices=1,
        plan="demo",
        note="License demo de test",
    )
    print("Demo license:", key)
    print("Admin key (default): admin123  -- doi bang bien moi truong ADMIN_KEY")
