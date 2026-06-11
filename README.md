# Logistics Apps — Product Verification & POD

Two full-stack web apps built with **FastAPI + Streamlit**, deployed on free-tier cloud services.

---

## Apps at a Glance

| | App 1 — Product Verification | App 2 — Proof of Delivery (POD) |
|---|---|---|
| **Users** | Warehouse Manager, Operator, QA | Delivery Driver |
| **Backend port** | 8000 | 8001 |
| **Frontend port** | 8501 | 8502 |
| **Key features** | Bulk CSV import (background job), WID lookup, photo capture, date-range reports | AWB barcode scan, photo/video upload, delivery log |

---

## Architecture

```
┌─────────────────────────────────┐   ┌──────────────────────────────────┐
│       App 1 — Verification      │   │          App 2 — POD              │
│                                 │   │                                  │
│  Streamlit (3 pages)            │   │  Streamlit (3 pages)             │
│    ↓ HTTP                       │   │    ↓ HTTP                        │
│  FastAPI                        │   │  FastAPI                         │
│    ├─ POST /upload  (async job) │   │    ├─ POST /media/upload          │
│    ├─ GET  /verify/{wid}        │   │    ├─ POST /deliveries            │
│    ├─ POST /verify/{wid}/log    │   │    └─ GET  /deliveries[/{awb}]   │
│    └─ GET  /report              │   │                                  │
│    ↓                            │   │    ↓                             │
│  SQLite / PostgreSQL            │   │  SQLite / PostgreSQL             │
│  + Cloudinary (photos)          │   │  + Cloudinary (photos + videos)  │
└─────────────────────────────────┘   └──────────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| **Background CSV import** | `POST /upload` returns a job ID instantly. A background thread streams the CSV in 5,000-row chunks. Frontend polls `/jobs/{id}` for live progress. No timeout, no blocking. |
| **`csv.DictReader` (not Pandas)** | Lower memory footprint; truly streaming. Pandas `read_csv` buffers the whole chunk. |
| **`ON CONFLICT (wid) DO NOTHING`** | One duplicate WID cannot abort the whole batch. Returns `inserted` + `duplicate` counts per job. |
| **Indexed `checked_at`** | Report queries filter by date range — this index makes them fast even at millions of rows. |
| **Paginated `/report`** | Never returns unbounded result sets to the frontend. Max 1,000 rows per page. |
| **Cloudinary** | 25 GB free storage + CDN. No S3 bucket or IAM policy setup. |
| **Proper user identity** | `username` field (not a hard-coded "operator") is passed from the Streamlit sidebar into every verification log. |

---

## Prerequisites

- Python 3.11+
- Docker + Docker Compose (for container-based local dev)
- A free [Cloudinary](https://cloudinary.com) account

---

## Local Setup (without Docker)

### 1. Clone and configure

```bash
git clone <repo-url>
cd project
cp .env.example .env
# Edit .env and fill in your Cloudinary credentials
```

### 2. Run App 1 backend

```bash
cd app1_verification/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### 3. Run App 1 frontend

```bash
cd app1_verification/frontend
pip install -r requirements.txt
API_URL=http://localhost:8000 streamlit run app.py --server.port 8501
```

### 4. Run App 2 backend

```bash
cd app2_pod/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### 5. Run App 2 frontend

```bash
cd app2_pod/frontend
pip install -r requirements.txt
API_URL=http://localhost:8001 streamlit run app.py --server.port 8502
```

> **Note for macOS / Linux:** `pyzbar` requires `zbar` to be installed:
> - macOS: `brew install zbar`
> - Ubuntu/Debian: `sudo apt-get install libzbar0`

---

## Local Setup (Docker Compose — recommended)

```bash
cp .env.example .env   # fill in Cloudinary keys
docker compose up --build
```

| Service | URL |
|---|---|
| App 1 frontend | http://localhost:8501 |
| App 1 backend (Swagger) | http://localhost:8000/docs |
| App 2 frontend | http://localhost:8502 |
| App 2 backend (Swagger) | http://localhost:8001/docs |

---

## Test the CSV Import

```bash
# Upload the sample file (App 1 must be running)
curl -X POST http://localhost:8000/api/upload \
  -F "file=@scripts/sample_products.csv"
# Returns: {"job_id": 1, "message": "..."}

# Poll progress
curl http://localhost:8000/api/jobs/1
```

---

## Free-Tier Deployment

### Step 1 — Supabase (PostgreSQL)

1. Create a free project at [supabase.com](https://supabase.com)
2. Copy the **URI** from Project Settings → Database → Connection string
3. Use it as `DATABASE_URL` in Render (below)

### Step 2 — Render (FastAPI backends)

1. Push each `backend/` folder to a separate GitHub repo (or monorepo with path filter)
2. New → Web Service → connect repo
3. **Build command:** `pip install -r requirements.txt`
4. **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add env vars: `DATABASE_URL`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
6. Deploy — Render provides a public HTTPS URL

### Step 3 — Streamlit Community Cloud (frontends)

1. Push each `frontend/` folder to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Select repo + `app.py`
4. Add **secrets** (Settings → Secrets):

```toml
API_URL = "https://your-render-backend-url.onrender.com"
```

5. Deploy — Streamlit provides a public HTTPS URL

---

## Project Structure

```
project/
├── app1_verification/
│   ├── backend/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── database.py              # SQLAlchemy engine + session
│   │   ├── models.py                # Product, VerificationLog, ImportJob
│   │   ├── cloudinary_helper.py     # Upload helper
│   │   ├── routers/
│   │   │   ├── upload.py            # Async CSV import + job polling
│   │   │   ├── verify.py            # WID lookup + audit log
│   │   │   └── reports.py           # Paginated date-range report
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── frontend/
│       ├── app.py                   # Landing page + sidebar nav
│       ├── pages/
│       │   ├── 1_Upload.py          # CSV upload + live progress bar
│       │   ├── 2_Verify.py          # WID scan, photo, log
│       │   └── 3_Reports.py         # Date-range reports + CSV export
│       ├── requirements.txt
│       └── Dockerfile
│
├── app2_pod/
│   ├── backend/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py                # Delivery
│   │   ├── cloudinary_helper.py
│   │   ├── routers/
│   │   │   └── pod.py               # Media upload + delivery CRUD
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── frontend/
│       ├── app.py
│       ├── pages/
│       │   ├── 1_Scan_AWB.py        # Camera + pyzbar barcode decode
│       │   ├── 2_Capture_Media.py   # Photo/video capture + POD submit
│       │   └── 3_Delivery_Log.py    # Paginated log + search by AWB
│       ├── requirements.txt
│       └── Dockerfile
│
├── scripts/
│   └── sample_products.csv          # Test data for upload endpoint
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Scalability Notes (for interview discussion)

- **Millions of CSV rows:** Streaming `csv.DictReader` + 5,000-row commit chunks means memory usage is flat regardless of file size. Background thread means no HTTP timeout.
- **Large report date ranges:** DB-side `WHERE checked_at BETWEEN` with an index, plus server-side pagination — the API never loads more than 1,000 rows into memory at once.
- **Production upgrade path:** Replace SQLite with Supabase PostgreSQL (one env var change). Add a task queue (Celery + Redis) to replace the background thread for horizontal scaling. Replace Streamlit with React/React Native for a mobile-first operator UX.
