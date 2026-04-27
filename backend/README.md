# Face Clustering Attendance System — Backend

A production-ready FastAPI backend for automated face-based attendance using InsightFace (buffalo_l model), PostgreSQL with pgvector, and JWT authentication.

## Features

- **Face Detection & Recognition**: InsightFace buffalo_l model with 512-dim embeddings
- **Automatic Attendance**: Upload group images → detect faces → match students → mark attendance
- **Background Processing**: Async ML processing with task status polling
- **Unknown Face Management**: Store and later assign unidentified faces
- **Export**: CSV and Excel attendance reports
- **JWT Authentication**: Secure admin/teacher access with role-based permissions
- **Rate Limiting**: In-memory sliding window (10/min uploads, 100/min general)
- **pgvector Search**: IVFFlat indexed cosine similarity for fast embedding matching

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI (async) |
| Database | PostgreSQL 14+ with pgvector |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| ML/AI | InsightFace + ONNX Runtime (CPU) |
| Auth | JWT (python-jose) + bcrypt |
| Validation | Pydantic v2 |

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- ~500MB disk space (InsightFace model download)

### Step-by-Step Setup

```bash
# 1. Clone and navigate to backend
cd backend

# 2. Copy environment variables
cp .env.example .env
# Edit .env with your settings (change SECRET_KEY and JWT_SECRET_KEY!)

# 3. Start PostgreSQL with pgvector
docker-compose up -d

# 4. Create virtual environment and install dependencies
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -e .

# 5. Download InsightFace model (first time only, ~300MB)
python scripts/download_model.py

# 6. Run database migrations
alembic upgrade head

# 7. Create default admin user
python scripts/init_admin.py
# Creates: admin@example.com / Admin123!

# 8. Start the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Verify Setup

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Login, returns JWT tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Logout (client-side) |
| GET | `/api/v1/auth/me` | Current user info |

### Students
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/students` | Create student |
| GET | `/api/v1/students` | List students (paginated) |
| GET | `/api/v1/students/{id}` | Get student details |
| PUT | `/api/v1/students/{id}` | Update student |
| DELETE | `/api/v1/students/{id}` | Soft-delete student |
| POST | `/api/v1/students/{id}/images` | Add face images (max 5) |
| DELETE | `/api/v1/students/{id}/images/{img_id}` | Delete image |

### Attendance
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/attendance/process-group` | Upload group image → task_id |
| GET | `/api/v1/attendance` | List attendance (filtered) |
| POST | `/api/v1/attendance/manual` | Manual mark |
| PUT | `/api/v1/attendance/{id}` | Update status |
| DELETE | `/api/v1/attendance/{id}` | Delete record |
| GET | `/api/v1/attendance/export` | CSV/Excel export |

### Unknown Faces
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/unknown-faces` | List unknown faces |
| GET | `/api/v1/unknown-faces/{id}/image` | Get image |
| POST | `/api/v1/unknown-faces/{id}/assign` | Assign to student |
| DELETE | `/api/v1/unknown-faces/{id}` | Delete |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/tasks/{task_id}/status` | Poll processing status |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | DB + ML model status |
| GET | `/metrics` | Basic metrics |

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app with lifespan
│   ├── core/                # Config, security, middleware
│   ├── db/                  # SQLAlchemy async session
│   ├── models/              # ORM models (pgvector)
│   ├── schemas/             # Pydantic v2 schemas
│   ├── api/v1/              # API route handlers
│   ├── services/            # Business logic
│   ├── ml/                  # InsightFace singleton + matcher
│   ├── utils/               # File upload, logging, validators
│   └── dependencies/        # FastAPI DI (auth, db)
├── alembic/                 # Database migrations
├── uploads/                 # Uploaded images
├── models/                  # InsightFace model files
├── scripts/                 # Setup scripts
├── tests/                   # Test suites
├── docker-compose.yml       # PostgreSQL + pgvector
├── pyproject.toml           # Dependencies
└── .env                     # Environment variables
```

## Configuration

All settings are loaded from `.env`. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `COSINE_SIMILARITY_THRESHOLD` | `0.6` | Face matching threshold |
| `FACE_DETECTION_THRESHOLD` | `0.5` | Minimum detection confidence |
| `MAX_UPLOAD_SIZE_MB` | `10` | Max upload file size |
| `RATE_LIMIT_UPLOAD` | `10` | Upload requests/minute/user |
| `JWT_EXPIRY_HOURS` | `24` | Token expiration |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Type checking
mypy app/ --strict

# Linting
ruff check app/
```

## License

MIT
