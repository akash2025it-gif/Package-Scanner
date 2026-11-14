from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import init_db, seed_demo_users
from app.core.exceptions import PackCheckException, packcheck_exception_handler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
ROOT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
FRONTEND_DIST = os.path.join(ROOT_DIR, "frontend", "dist")
ASSETS_DIR = os.path.join(FRONTEND_DIST, "assets")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed demo users safely
    try:
        await init_db()
        await seed_demo_users()
    except Exception as e:
        print(f"Database initialization warning: {e}")
    
    # Ensure upload, static & reports directories exist safely
    for directory in [settings.LOCAL_STORAGE_DIR, settings.REPORTS_DIR, STATIC_DIR]:
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception:
            pass
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## PackCheck — AI-assisted Legal Metrology Compliance Scanner Backend & APIs
    
    PackCheck is a regulatory compliance verification platform for the **Legal Metrology (Packaged Commodities) Rules, 2011**.
    
    ### Key Capabilities:
    - **Label Ingestion & Preprocessing:** Upload high-resolution photographs of packaged goods.
    - **Pluggable AI & OCR:** Multi-region detection + OCR with Google Cloud Vision / Tesseract / Mock providers.
    - **Config-Driven Rule Engine:** Complete LMPC 2011 compliance checks (MRP format, tax inclusivity, net quantity units per Rule 8, Second Schedule font height slabs, mfg dates, consumer care).
    - **Inspector Review & Overrides:** Legal workflow with full immutable audit trails.
    - **Document Generation:** High-fidelity statutory PDF and editable DOCX compliance reports.
    - **Enforcement Analytics:** Aggregated regional heatmaps, violation category breakdowns, and officer throughput metrics.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Register custom exception handler
app.add_exception_handler(PackCheckException, packcheck_exception_handler)

# Include v1 API Router (both with and without /api prefix for Vercel serverless compatibility)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(api_router, prefix="/v1")

# Mount static and SPA asset files
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Interactive UI Routes
@app.get("/", response_class=FileResponse)
async def serve_root():
    spa_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(spa_index):
        return FileResponse(spa_index)
    login_path = os.path.join(STATIC_DIR, "login.html")
    if os.path.exists(login_path):
        return FileResponse(login_path)
    return JSONResponse({
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    })


@app.get("/login", response_class=FileResponse)
async def serve_login():
    spa_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(spa_index):
        return FileResponse(spa_index)
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))


@app.get("/dashboard", response_class=FileResponse)
async def serve_dashboard():
    spa_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(spa_index):
        return FileResponse(spa_index)
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))


@app.get("/scan/new", response_class=FileResponse)
async def serve_scan_new():
    spa_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(spa_index):
        return FileResponse(spa_index)
    return FileResponse(os.path.join(STATIC_DIR, "scan_new.html"))


@app.get("/scan/{id}", response_class=FileResponse)
async def serve_scan_detail(id: str):
    spa_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(spa_index):
        return FileResponse(spa_index)
    return FileResponse(os.path.join(STATIC_DIR, "analysis.html"))


@app.get("/scan/{id}/processing", response_class=FileResponse)
async def serve_scan_processing(id: str):
    spa_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(spa_index):
        return FileResponse(spa_index)
    return FileResponse(os.path.join(STATIC_DIR, "analysis.html"))


@app.get("/analysis", response_class=FileResponse)
async def serve_analysis():
    spa_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(spa_index):
        return FileResponse(spa_index)
    return FileResponse(os.path.join(STATIC_DIR, "analysis.html"))


@app.get("/history", response_class=FileResponse)
async def serve_history():
    spa_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(spa_index):
        return FileResponse(spa_index)
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))


@app.get("/review-queue", response_class=FileResponse)
async def serve_review_queue():
    spa_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(spa_index):
        return FileResponse(spa_index)
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))


@app.get("/reports", response_class=FileResponse)
async def serve_reports():
    spa_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(spa_index):
        return FileResponse(spa_index)
    return FileResponse(os.path.join(STATIC_DIR, "report.html"))


@app.get("/rules", response_class=FileResponse)
async def serve_rules():
    spa_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(spa_index):
        return FileResponse(spa_index)
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))


@app.get("/analytics", response_class=FileResponse)
async def serve_analytics():
    spa_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(spa_index):
        return FileResponse(spa_index)
    return FileResponse(os.path.join(STATIC_DIR, "enforcement.html"))


@app.get("/settings", response_class=FileResponse)
async def serve_settings():
    spa_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(spa_index):
        return FileResponse(spa_index)
    return FileResponse(os.path.join(STATIC_DIR, "team.html"))


@app.get("/products-ui", response_class=FileResponse)
async def serve_products_ui():
    return FileResponse(os.path.join(STATIC_DIR, "products.html"))


@app.get("/enforcement", response_class=FileResponse)
async def serve_enforcement():
    return FileResponse(os.path.join(STATIC_DIR, "enforcement.html"))


@app.get("/team", response_class=FileResponse)
async def serve_team():
    return FileResponse(os.path.join(STATIC_DIR, "team.html"))


@app.get("/batch/{batch_number}", response_class=FileResponse)
async def serve_batch_detail(batch_number: str):
    return FileResponse(os.path.join(STATIC_DIR, "batch_detail.html"))


@app.get("/batches-ui", response_class=FileResponse)
async def serve_batches_ui():
    return FileResponse(os.path.join(STATIC_DIR, "batch_detail.html"))


@app.get("/api/health")
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "database": "connected",
    }


@app.get("/api/info")
async def get_api_info():
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
