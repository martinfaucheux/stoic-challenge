# Database Setup Guide

This guide explains how to set up PostgreSQL for the Email Security Tool.

## Prerequisites

- PostgreSQL 14+ installed
- Python 3.13+
- Docker (optional, for containerized setup)

## Option 1: Local PostgreSQL Installation

### macOS (using Homebrew)

```bash
# Install PostgreSQL
brew install postgresql@16

# Start PostgreSQL service
brew services start postgresql@16

# Create database
createdb email_security

# Create user (optional)
psql postgres
CREATE USER email_security_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE email_security TO email_security_user;
\q
```

### Linux (Ubuntu/Debian)

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql
CREATE DATABASE email_security;
CREATE USER email_security_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE email_security TO email_security_user;
\q
```

## Option 2: Docker PostgreSQL

```bash
# Run PostgreSQL in Docker
docker run --name email-security-db \
  -e POSTGRES_DB=email_security \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  -d postgres:16

# Stop container
docker stop email-security-db

# Start existing container
docker start email-security-db
```

## Configuration

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and update the `DATABASE_URL`:

   ```bash
   # Default (matches Docker setup):
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/email_security

   # Or with custom user:
   DATABASE_URL=postgresql+asyncpg://email_security_user:your_password@localhost:5432/email_security
   ```

## Running Migrations

After PostgreSQL is running and configured:

```bash
# Install dependencies
uv sync

# Create initial migration (if not already created)
uv run alembic revision --autogenerate -m "Add email table"

# Apply migrations
uv run alembic upgrade head

# Check migration status
uv run alembic current

# Rollback last migration
uv run alembic downgrade -1
```

## Verify Database Setup

```bash
# Connect to database
psql postgresql://postgres:postgres@localhost:5432/email_security

# List tables
\dt

# Describe emails table
\d emails

# Exit
\q
```

## Troubleshooting

### Connection refused error

- Ensure PostgreSQL is running: `brew services list` (macOS) or `sudo systemctl status postgresql` (Linux)
- Check port 5432 is available: `lsof -i :5432`

### Authentication failed

- Verify credentials in `DATABASE_URL`
- Check PostgreSQL user permissions

### Migration errors

- Ensure database exists
- Check alembic configuration in `alembic.ini` and `alembic/env.py`
- Verify models are imported correctly in `alembic/env.py`
