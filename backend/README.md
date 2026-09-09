# PackCheck — AI-Assisted Legal Metrology Compliance Scanner (Backend & APIs)

PackCheck is a regulatory compliance verification platform engineered for the **Legal Metrology (Packaged Commodities) Rules, 2011 (LMPC Rules)** and Section 36 of the Legal Metrology Act, 2009.

It empowers enforcement officers and automated e-commerce monitoring pipelines to ingest packaged commodity label photographs, run AI-assisted region detection + OCR, validate against statutory mandatory declarations & Second Schedule font size regulations, review/override AI verdicts with legal notes, and generate legally defensible PDF and editable DOCX compliance reports.

---

## 🏗️ Architecture & Features

- **FastAPI (Async Python 3.11):** High-throughput, asynchronous RESTful API with auto-generated OpenAPI / Swagger docs.
- **SQLAlchemy 2.0 (Async) + Alembic:** Production PostgreSQL / local SQLite async support with schema migrations.
- **Config-Driven LMPC Rule Engine:** Declarative YAML rules (`lmpc_rules.yaml` & `font_size_tables.yaml`) covering:
  - **Rule 6(1)(a):** Common / generic name of commodity
  - **Rule 6(1)(b):** Manufacturer / packer / importer name & address
  - **Rule 6(1)(c):** Country of origin (imported goods)
  - **Rule 6(1)(d) & Rule 8:** Net quantity in standard metric units ($g, kg, ml, l, N$)
  - **Rule 6(1)(e):** Month & year of manufacture / packing / import
  - **Rule 6(1)(f):** Maximum Retail Price (MRP) with currency symbol ($₹, Rs.$) and mandatory *"inclusive of all taxes"* clause
  - **Rule 6(1)(g):** Unit Sale Price (USP)
  - **Rule 6(1)(h):** Consumer care contact details (telephone / toll-free, email, grievance officer)
  - **Second Schedule:** Font size / numeral height validation based on net-quantity weight/volume slabs ($1.0\text{mm} \to 8.0\text{mm}$).
- **Pluggable AI / OCR Pipeline:** Pluggable `OCRProvider` (Google Cloud Vision API, Tesseract OCR, Deterministic Mock) + `RegionDetector` (YOLOv8 / Detectron2 / Heuristic) + `FontSizeCalibrator` with pixel-to-mm scaling.
- **Role-Based Access Control (RBAC):** JWT Access/Refresh tokens for `Inspector` and `Admin`.
- **Immutable Audit Trail:** All review overrides, status updates, and report generation events are logged in `AuditLog`.
- **Statutory Document Generation:** High-fidelity PDF reports via WeasyPrint and editable Word documents via `python-docx`.
- **Enforcement Analytics:** Regional heatmaps, violation category distributions, and officer throughput metrics.

---

## 🚀 Quickstart Guide

### Option 1: Run with Docker Compose (Full Stack)

```bash
cd backend
docker-compose up --build
```
This spins up:
- **PackCheck API:** `http://localhost:8000`
- **Swagger Docs:** `http://localhost:8000/docs`
- **PostgreSQL 16:** `localhost:5432`
- **Redis 7:** `localhost:6379`
- **MinIO Object Storage:** `http://localhost:9000` (Console: `http://localhost:9001`, user: `minioadmin`, pass: `minioadmin`)
- **Celery Worker:** 2 background concurrency workers

---

### Option 2: Run Locally (Python 3.11+)

1. **Install Dependencies:**
   ```bash
   cd backend
   pip install -r requirements-dev.txt
   ```

2. **Initialize Database and Seed Demo Data:**
   ```bash
   python scripts/seed_data.py
   ```

3. **Start the API Server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the Interactive API Documentation:**
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 👥 Default Demo Accounts

| Role | Email | Password | Scope / Region |
|---|---|---|---|
| **Admin** | `admin@packcheck.gov.in` | `admin123` | Full access, user management |
| **Inspector** | `inspector.sharma@packcheck.gov.in` | `inspector123` | Full scan & inspection verification (Delhi NCR) |
| **Inspector** | `inspector.reddy@packcheck.gov.in` | `inspector123` | Full scan & inspection verification (Karnataka) |
| **Inspector** | `inspector.rao@packcheck.gov.in` | `inspector123` | Full scan & inspection verification (Maharashtra) |

*For phone login, any registered phone with OTP `123456` will authenticate.*

---

## 📡 Core API Endpoints

### Authentication & Users
- `POST /api/v1/auth/login` — Authenticate via email+password or phone+OTP
- `POST /api/v1/auth/refresh` — Refresh access token
- `GET /api/v1/auth/me` — Current officer profile & role
- `GET /api/v1/users` — List system users (Admin only)
- `POST /api/v1/users` — Create officer account (Admin only)

### Compliance Scans & AI Pipeline
- `POST /api/v1/scans` — Initialize new scan (metadata + product link)
- `POST /api/v1/scans/{id}/images` — Upload label photographs
- `POST /api/v1/scans/{id}/analyze` — Trigger async AI pipeline (rate-limited)
- `GET /api/v1/scans/{id}` — Full scan detail with bounding boxes & rule verdicts
- `PATCH /api/v1/scans/{id}/declarations/{decl_id}` — Reviewer override with legal notes
- `POST /api/v1/scans/{id}/close` — Close and conclude scan
- `GET /api/v1/scans` — Filter and search scans (by date, status, brand, category, region)

### Reports & Analytics
- `POST /api/v1/scans/{id}/report` — Generate statutory PDF + editable DOCX report
- `GET /api/v1/reports/{id}/pdf` — Stream / download PDF report
- `GET /api/v1/reports/{id}/docx` — Stream / download editable Word report
- `GET /api/v1/analytics/summary` — High-level compliance KPIs and trends
- `GET /api/v1/analytics/region-heatmap` — Regional violation heatmaps
- `GET /api/v1/analytics/officer-performance` — Inspector throughput metrics

---

## 🧪 Running Automated Tests

Run the full pytest suite:

```bash
cd backend
pytest -v
```

To view coverage:
```bash
pytest --cov=app --cov-report=term-missing
```

---

## 📦 Exporting Postman Collection & OpenAPI Specs

```bash
python scripts/export_postman.py
```
This generates:
- `openapi.json`
- `packcheck_postman_collection.json` (ready to import directly into Postman)
