"""WSGI entry point for PythonAnywhere / any WSGI host (no gunicorn needed)."""
from app import create_app

application = create_app()

# PythonAnywhere looks for `application`; some hosts look for `app`.
app = application
