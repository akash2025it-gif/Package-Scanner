"""
Vercel Serverless Function entry point for PackCheck AI.
Exposes the FastAPI application for /api/* routes on Vercel.
"""

import os
from pathlib import Path
import sys
import traceback

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent if CURRENT_DIR.name == "api" else CURRENT_DIR
BACKEND_DIR = ROOT_DIR / "backend"

for p in [str(BACKEND_DIR), str(ROOT_DIR), "/var/task/backend", "/var/task"]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

os.environ["VERCEL"] = "1"

try:
    from app.main import app  # noqa: E402
except Exception as exc:
    tb = traceback.format_exc()
    print(f"CRITICAL startup failure: {exc}\n{tb}", file=sys.stderr)
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="PackCheck API Recovery Handler")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def fallback_handler(full_path: str):
        return JSONResponse(
            status_code=200 if "health" in full_path else 500,
            content={
                "status": "degraded",
                "message": "PackCheck API initialization reported an error",
                "error": str(exc),
                "traceback": tb,
                "path": full_path,
            }
        )
