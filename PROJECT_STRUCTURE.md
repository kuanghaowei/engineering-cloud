# AEC Collaboration Platform - Project Structure

## Directory Layout

```
aec-collaboration-platform/
├── app/                          # Main application package
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # FastAPI application entry point
│   ├── config.py                # Configuration management
│   ├── database.py              # Database connection & session
│   ├── logging_config.py        # Logging configuration
│   └── celery_app.py            # Celery task queue setup
│
├── .kiro/                        # Kiro specs directory
│   └── specs/
│       └── aec-collaboration-platform/
│           ├── requirements.md   # Requirements document
│           ├── design.md        # Design document
│           └── tasks.md         # Implementation tasks
│
├── docker-compose.yml           # Infrastructure services
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (dev)
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore patterns
├── README.md                    # Project documentation
├── SETUP_VERIFICATION.md        # Setup verification report
└── setup.sh                     # Setup script (existing)
```

## Technology Stack

### Backend
- **Framework**: FastAPI 0.109.0
- **ORM**: SQLAlchemy 2.0.25 (async)
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **Task Queue**: Celery 5.3.6
- **Object Storage**: MinIO / Alibaba OSS

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Database Driver**: asyncpg (async PostgreSQL)
- **Configuration**: pydantic-settings + python-dotenv

## Configuration

### Environment Variables

All configuration is managed through environment variables defined in `.env`:

- **Database**: PostgreSQL connection string with asyncpg driver
- **Redis**: Redis connection for caching and Celery
- **MinIO**: Object storage endpoint and credentials
- **JWT**: Secret key and token expiration
- **Application**: Debug mode, log level, app metadata

### Docker Services

Three services are defined in `docker-compose.yml`:

1. **PostgreSQL 16**: Port 5432, persistent volume
2. **Redis 7**: Port 6379, persistent volume
3. **MinIO**: Ports 9000 (API) & 9001 (Console), persistent volume

All services include health checks and automatic restart policies.

## Application Architecture

### FastAPI Application (`app/main.py`)

- Async lifespan management for startup/shutdown
- CORS middleware for cross-origin requests
- Health check endpoints
- Automatic API documentation (Swagger/ReDoc)

### Database Layer (`app/database.py`)

- Async SQLAlchemy engine with connection pooling
- Session factory for dependency injection
- Automatic transaction management (commit/rollback)
- Base declarative class for ORM models

### Configuration (`app/config.py`)

- Type-safe settings using Pydantic
- Automatic environment variable loading
- Support for multiple storage backends
- Validation and default values

### Logging (`app/logging_config.py`)

- Structured logging with timestamps
- Configurable log levels
- Module-specific loggers
- Console output handler

### Task Queue (`app/celery_app.py`)

- Celery application with Redis broker
- JSON serialization for tasks
- Configurable worker settings
- Task time limits and prefetch control

## Development Workflow

### Initial Setup

```bash
# Start infrastructure
docker-compose up -d

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Terminal 1: FastAPI server
python -m app.main

# Terminal 2: Celery worker
celery -A app.celery_app worker --loglevel=info
```

### Accessing Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

## Next Steps

The project skeleton is complete. Next tasks include:

1. **Task 2**: Database models and migrations (Alembic)
2. **Task 3**: Authentication and tenant isolation
3. **Task 4**: Project and permission management
4. **Task 5**: Object storage adapter implementation

See `tasks.md` for the complete implementation plan.
