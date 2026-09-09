"""Vercel entry point for the PackCheck FastAPI application."""

from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
backend_dir_string = str(BACKEND_DIR)
if backend_dir_string not in sys.path:
    sys.path.insert(0, backend_dir_string)

from app.main import app  # noqa: E402
