"""
Vercel looks for Python functions inside an api/ folder. This file just
re-exposes the real Flask app (defined in app.py at the project root) so
Vercel's Python runtime can find it, without duplicating any logic.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app import app  # noqa: E402  (the actual Flask app + all routes)
