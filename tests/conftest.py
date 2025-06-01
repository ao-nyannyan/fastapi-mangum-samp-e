import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.database import Base, get_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(TEST_DATABASE_URL, future=True)
AsyncSessionTest = sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
async def initialized_app():
    # recreate tables
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # override dependency
    async def override_get_db():
        async with AsyncSessionTest() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db
    yield app

@pytest.fixture
async def client(initialized_app):
    async with AsyncClient(app=initialized_app, base_url="http://test") as ac:
        yield ac
