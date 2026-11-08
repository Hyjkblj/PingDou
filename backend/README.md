# PingDou Backend

FastAPI backend for the one-code, one-project PingDou pattern service.

## Local Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
docker compose up -d mysql
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

API documentation is available at `http://127.0.0.1:8000/docs`. The local SMS code is
`123456`; the seed command prints a development redemption code.

MySQL listens on 127.0.0.1:3306. The development database, user and password are
pingdou, pingdou and pingdou_dev. Schema creation and upgrades must go through
Alembic; application startup does not create tables implicitly.

When an existing local MySQL service is used instead of Docker, initialize the development
database once with an administrator account:

    mysql.exe -u root -p -e "SOURCE scripts/mysql_bootstrap.sql"
    alembic upgrade head
    python -m scripts.seed

Existing SQLite files are left untouched and are not imported automatically.

## Image Storage

Image and export binaries are not stored in MySQL. The current development adapter writes them
under backend/storage/ using keys such as:

    users/{userId}/projects/{projectId}/source/{assetId}.png
    users/{userId}/projects/{projectId}/derived/{assetId}.png
    users/{userId}/projects/{projectId}/exports/{exportId}.pdf

MySQL stores only asset metadata and the storage_key: ownership, type, file name, MIME type,
byte size, image dimensions, SHA-256 and processing metadata. LocalStorage is isolated behind
app/core/storage.py; MinIO/S3 settings are reserved for replacing the local adapter in deployment.

## Architecture

Each business capability owns its router, schemas and service. Shared persistence models live in
`app/domain`, project authorization lives in `app/domain/access.py`, and local file storage is behind
`app/core/storage.py`. Image AI and background removal use a replaceable provider in
`app/imaging/provider.py`.

Development defaults to eager job execution so frontend integration needs no Celery worker. Set
`PINGDOU_JOB_EAGER=false` and run Redis/Celery when connecting production providers.

## Checks

```powershell
python -m compileall -q app tests scripts
python -m ruff check app tests scripts
python -m pytest
```

The end-to-end test covers payment callback idempotency, code redemption, upload validation,
background removal, white-preview semantics, pattern editing conflicts and PNG/PDF/CSV exports.
