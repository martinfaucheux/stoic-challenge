import uuid
from datetime import timedelta
from typing import Awaitable, Callable

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

import models  # noqa Import models to register them with SQLAlchemy
from main import app
from models import UserTable
from services.auth import create_access_token
from services.database import Base, get_db  # Import Base from database service
from tests.factories import EmailFactory, UserFactory

# Models are imported above to register them with SQLAlchemy

# Generate a unique test database name for this test session
TEST_DB_NAME = f"test_database_{uuid.uuid4().hex[:8]}.db"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def ensure_test_database():
    """Clean up any existing test database file."""
    import os

    if os.path.exists(TEST_DB_NAME):
        os.remove(TEST_DB_NAME)
    print(f"Cleaned up test database file: {TEST_DB_NAME}")

    # Cleanup after tests complete
    yield

    if os.path.exists(TEST_DB_NAME):
        os.remove(TEST_DB_NAME)
        print(f"Cleaned up test database file after tests: {TEST_DB_NAME}")


async_engine = create_async_engine(
    url=f"sqlite+aiosqlite:///./{TEST_DB_NAME}",
    echo=False,
    poolclass=NullPool,
)


@pytest_asyncio.fixture(scope="session")
async def async_db_engine():
    # Create tables once per test session
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_engine

    # Clean up after all tests
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def async_db(async_db_engine):
    async_session = async_sessionmaker(
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
        bind=async_db_engine,
        class_=AsyncSession,
    )

    async with async_session() as session:
        await session.begin()

        yield session

        await session.rollback()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def async_client(async_db):
    def override_get_db():
        yield async_db

    app.dependency_overrides[get_db] = override_get_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost")


@pytest_asyncio.fixture(scope="function")
async def user_factory(async_db) -> Callable[..., Awaitable[UserTable]]:
    async def factory_create(**kwargs) -> UserTable:
        return await UserFactory.create_async(async_db, **kwargs)

    return factory_create


@pytest_asyncio.fixture(scope="function")
async def email_factory(async_db) -> Callable[..., Awaitable]:
    async def factory_create(**kwargs):
        return await EmailFactory.create_async(async_db, **kwargs)

    return factory_create


@pytest_asyncio.fixture(scope="function")
async def test_user(async_db) -> UserTable:
    """Create a test user in the database with a unique email"""

    unique_email = f"test_{uuid.uuid4()}@example.com"
    return await UserFactory.create_async(async_db, email=unique_email, commit=False)


@pytest_asyncio.fixture(scope="function")
async def create_user(user_factory) -> Callable[[str], Awaitable[UserTable]]:
    """
    Backward-compatible user factory fixture.

    Usage:
        user = await create_user("user1@example.com")
    """

    async def user_factory_wrapper(email: str) -> UserTable:
        return await user_factory(email=email)

    return user_factory_wrapper


@pytest_asyncio.fixture(scope="function")
async def get_client(async_db) -> Callable[[UserTable], AsyncClient]:
    """
    Client factory fixture that creates an authenticated client for a given user.
    This fixture solves 401 authentication errors in tests by automatically
    creating and attaching JWT tokens for API requests.

    Usage:
        # With test_user fixture
        client = get_client(test_user)
        response = await client.get("/emails")

        # With custom user
        user = await create_user("myuser@example.com")
        client = get_client(user)
        response = await client.post("/some-protected-endpoint")
    """

    def override_get_db():
        yield async_db

    app.dependency_overrides[get_db] = override_get_db

    def client_factory(user: UserTable) -> AsyncClient:
        # Create JWT token for the user
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=timedelta(minutes=30)
        )

        # Create client with Authorization header
        return AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    return client_factory
