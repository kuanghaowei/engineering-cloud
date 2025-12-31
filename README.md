# AEC Collaboration Platform

跨单位工程协同平台 - 支持多租户、大文件版本控制、BIM/CAD预览、数字印章审批等核心功能。

## Architecture

- **Web Framework**: FastAPI (Python)
- **Database**: PostgreSQL
- **Object Storage**: MinIO / Alibaba OSS
- **Task Queue**: Celery + Redis
- **ORM**: SQLAlchemy 2.0

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Docker & Docker Compose

### 2. Setup

```bash
# Clone repository
git clone <repository-url>
cd aec-collaboration-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env
# Edit .env with your configuration

# Start infrastructure services
docker-compose up -d

# Wait for services to be healthy
docker-compose ps
```

### 3. Run Application

```bash
# Run FastAPI application
python -m app.main

# Or use uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Run Celery Worker

```bash
# In a separate terminal
celery -A app.celery_app worker --loglevel=info
```

## API Documentation

Once the application is running, visit:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── database.py          # Database connection
│   ├── logging_config.py    # Logging setup
│   └── celery_app.py        # Celery configuration
├── docker-compose.yml       # Infrastructure services
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
└── README.md
```

### Infrastructure Services

- **PostgreSQL**: Port 5432
- **Redis**: Port 6379
- **MinIO**: Port 9000 (API), 9001 (Console)

### MinIO Console

Access MinIO console at http://localhost:9001
- Username: minioadmin
- Password: minioadmin

## License

Proprietary
