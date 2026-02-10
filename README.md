# Email Security Service

FastAPI-based email security tool to detect potential financial fraud attempts in emails received via Google Workspace and Microsoft O365.

## Requirements

- Docker and Docker Compose
- Gmail API credentials (see [gmail/GMAIL_SETUP.md](gmail/GMAIL_SETUP.md))

## Quick Start with Docker

### 1. Setup Gmail Credentials

Ensure you have `gmail/credentials.json` and `gmail/token.json` in place. See [gmail/GMAIL_SETUP.md](gmail/GMAIL_SETUP.md) for instructions.

### 2. Configure Environment Variables

Copy the Docker environment template:

```bash
cp .env.docker .env
```

Edit `.env` if you need to customize database credentials or other settings.

### 3. Build and Start Services

```bash
docker compose up -d
```

This starts:

- PostgreSQL database on port 5432
- FastAPI web server on port 8000

### 4. Run Database Migrations

```bash
docker compose run web alembic upgrade head
```

### 5. Verify Services

Check the API health endpoint:

```bash
curl http://localhost:8000/
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

- `GET /` - Health check
- `GET /emails` - Retrieve all emails
- `GET /emails/{id}` - Retrieve specific email
- `POST /webhook` - Receive email webhooks

## Development

For local development without Docker, see [DATABASE_SETUP.md](DATABASE_SETUP.md).

## Project Structure

- `main.py` - FastAPI application
- `models.py` - SQLAlchemy database models
- `database.py` - Database configuration
- `config.py` - Application configuration
- `gmail/` - Gmail API integration
- `alembic/` - Database migrations
