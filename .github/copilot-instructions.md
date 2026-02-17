## Introduction

We want to build an **Email Security** tool to flag emails with potential financial fraud attempts (fake president, fake supplier, etc.) that are received by our clients. We focus on clients that are using Google Workspace and Microsoft O365 so users and emails can be retrieved through relevant APIs.

The goal is to code the service retrieving the emails.

## Requirements

- Build the service in Python with FastAPI
- Use PostgreSQL
  - use SQLAlchemy as the ORM
  - use Alembic for migrations
- Dockerize the service
- Tests using pytest
