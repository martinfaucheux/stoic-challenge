# Email Security Service

FastAPI-based email security tool to detect potential financial fraud attempts in emails received via Google Workspace and Microsoft O365.

Currently, it is possible to connect a Google Workspace account, fetch and persist emails in the database.

Other notes regarded the assessment can be found in the [notes document](docs/NOTES.md).

## Requirements

- uv as python package manager
- Docker and Docker Compose

## Quick Start with Docker

### 1. Configure Environment Variables

Copy the Docker environment template:

```bash
cp .env.example .env
```

Edit `.env` if you need to customize database credentials or other settings.

### 2. Build and Start Services

```bash
docker compose up -d
```

This starts:

- PostgreSQL database on port 5432
- FastAPI web server on port 8000

### 3. Run Database Migrations

```bash
docker compose run web alembic upgrade head
```

### 4. Set up Google OAuth Credentials

Follow the instructions in the [Google OAuth Setup Guide](docs/GOOGLE_SERVER_SETUP.md) to create credentials and configure the callback URL.

## Tests

to run the tests, you can use the following command:

```bash
uv run web pytest -v
```

## Docker Commands

### Start services

```bash
docker compose up -d
```

### Stop services

```bash
docker compose down
```

### View logs

```bash
docker compose logs -f web
docker compose logs -f db
```

### Run migrations

```bash
docker compose run web alembic upgrade head
```

### Create a new migration

```bash
docker compose run web alembic revision --autogenerate -m "description"
```

### Access the database

```bash
docker compose exec db psql -U postgres -d email_security
```

### Rebuild after code changes

```bash
docker compose up -d --build
```

## API Endpoints

once running, the API doc is available at `http://localhost:8000/docs`.
