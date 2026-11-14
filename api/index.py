"""
Vercel Serverless Function entry point for PackCheck AI.
Exposes the FastAPI application for /api/* routes on Vercel.
"""

import os
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent if CURRENT_DIR.name == "api" else CURRENT_DIR
BACKEND_DIR = ROOT_DIR / "backend"

backend_path_str = str(BACKEND_DIR)
root_path_str = str(ROOT_DIR)

if backend_path_str not in sys.path:
    sys.path.insert(0, backend_path_str)
if root_path_str not in sys.path:
    sys.path.insert(0, root_path_str)

os.environ["VERCEL"] = "1"

from app.main import app  # noqa: E402
