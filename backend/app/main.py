from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import PackCheckException, packcheck_exception_handler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    await init_db()
    
    # Ensure upload, static & reports directories exist
    os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    os.makedirs(STATIC_DIR, exist_ok=True)
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

# Include v1 API Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Mount static files
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Interactive UI Routes
@app.get("/", response_class=FileResponse)
async def serve_root():
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
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))


@app.get("/dashboard", response_class=FileResponse)
async def serve_dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))


@app.get("/scan/new", response_class=FileResponse)
async def serve_scan_new():
    return FileResponse(os.path.join(STATIC_DIR, "scan_new.html"))


@app.get("/analysis", response_class=FileResponse)
async def serve_analysis():
    return FileResponse(os.path.join(STATIC_DIR, "analysis.html"))


@app.get("/report", response_class=FileResponse)
async def serve_report():
    return FileResponse(os.path.join(STATIC_DIR, "report.html"))


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


@app.get("/api/info")
async def get_api_info():
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
