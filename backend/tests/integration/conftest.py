import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.core.wait_strategies import PortWaitStrategy
from testcontainers.minio import MinioContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from src.core.database import Base
from src.media.infra.repo import SqlAttachmentRepository
from src.media.infra.s3 import S3Storage


@pytest.fixture(scope="session")
def minio_secret_key():
    return "minioadmin123"


@pytest.fixture(scope="session")
def minio_container(minio_secret_key):
    minio_container = (
        MinioContainer(
            image="quay.io/minio/minio", access_key="minioadmin", secret_key=minio_secret_key,
        )
        .waiting_for(PortWaitStrategy(port=9000))
        .with_env("MINIO_ROOT_USER", "minioadmin")
        .with_env("MINIO_ROOT_PASSWORD", minio_secret_key)
        .with_bind_ports(9000, 9000)
    )
    with minio_container as minio:
        client = minio.get_client()
        if not client.bucket_exists("test-bucket"):
            client.make_bucket("test-bucket")
        yield minio


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer(image="postgres:16.9", driver="asyncpg") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container():
    container = RedisContainer("redis:7-alpine")
    container.start()
    yield container
    container.stop()


@pytest.fixture
def redis_url(redis_container):
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)

    return f"redis://{host}:{port}/0"


@pytest.fixture
async def engine(postgres_container):
    engine = create_async_engine(
        url=postgres_container.get_connection_url(), echo=True, pool_pre_ping=True
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine):
    sessionmaker = async_sessionmaker(
        engine, class_=AsyncSession, autoflush=False, expire_on_commit=False
    )
    async with sessionmaker() as session:
        yield session


@pytest.fixture(scope="session")
def s3_storage(minio_container, minio_secret_key):
    return S3Storage(
        endpoint_url=f"http://{minio_container.get_container_host_ip()}:{minio_container.get_exposed_port(9000)}",
        access_key="minioadmin",
        secret_key=minio_secret_key,
        bucket_name="test-bucket",
    )


@pytest.fixture
def attachment_repo(session):
    return SqlAttachmentRepository(session)
