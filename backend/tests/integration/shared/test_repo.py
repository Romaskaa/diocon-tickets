import pytest
from sqlalchemy.exc import IntegrityError

from src.shared.infra.repos import SqlAlchemyRepository

from ..helpers import ExampleEntity, ExampleMapper, ExampleOrm


class SqlExampleRepository(SqlAlchemyRepository):
    model = ExampleOrm
    model_mapper = ExampleMapper


@pytest.fixture
def example_repo(session):
    return SqlExampleRepository(session)


@pytest.fixture
def sample_entity():
    return ExampleEntity(value="sample-value")


class TestSqlAlchemyRepository:
    @pytest.mark.asyncio
    async def test_create_success(self, session, example_repo, sample_entity):
        created_entity = await example_repo.create(sample_entity)
        await session.commit()

        assert isinstance(created_entity, ExampleEntity)
        assert created_entity.value == sample_entity.value
        assert created_entity.id == sample_entity.id
        assert created_entity.created_at == sample_entity.created_at
        assert created_entity.updated_at == sample_entity.updated_at

    @pytest.mark.asyncio
    async def test_create_failure_raises_integrity_error(self, session, example_repo):
        entity1 = ExampleEntity(value="some-value")
        entity2 = ExampleEntity(value="some-value")
        entity2.id = entity1.id

        await example_repo.create(entity1)
        await session.commit()
        await example_repo.create(entity2)

        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_create_and_read_success(self, session, example_repo, sample_entity):
        await example_repo.create(sample_entity)
        await session.commit()
        entity = await example_repo.read(sample_entity.id)

        assert isinstance(entity, ExampleEntity)
        assert entity.id == sample_entity.id
        assert entity.value == sample_entity.value
        assert entity.created_at == sample_entity.created_at
        assert entity.updated_at == sample_entity.updated_at

    @pytest.mark.asyncio
    async def test_read_returns_none(self, example_repo, sample_entity):
        entity = await example_repo.read(sample_entity.id)

        assert entity is None

    @pytest.mark.asyncio
    async def test_create_and_update_success(self, session, example_repo, sample_entity):
        await example_repo.create(sample_entity)
        await session.commit()
        updated_entity = await example_repo.update(sample_entity.id, value="updated-value")

        assert isinstance(updated_entity, ExampleEntity)
        assert updated_entity.id == sample_entity.id
        assert updated_entity.value == "updated-value"
        assert updated_entity.created_at == sample_entity.created_at
        assert updated_entity.updated_at != sample_entity.updated_at

    @pytest.mark.asyncio
    async def test_update_returns_none(self, example_repo, sample_entity):
        entity = await example_repo.update(sample_entity.id, value="updated-value")

        assert entity is None

    @pytest.mark.asyncio
    async def test_create_and_upsert_success(self, session, example_repo, sample_entity):
        await example_repo.create(sample_entity)
        await session.commit()

        sample_entity.value = "refreshed-value"
        await example_repo.upsert(sample_entity)
        await session.commit()

        entity = await example_repo.read(sample_entity.id)

        assert isinstance(entity, ExampleEntity)
        assert entity.id == sample_entity.id
        assert entity.value == "refreshed-value"
        assert entity.created_at == sample_entity.created_at
        assert entity.updated_at != sample_entity.updated_at

    @pytest.mark.asyncio
    async def test_create_and_delete_success(self, session, example_repo, sample_entity):
        await example_repo.create(sample_entity)
        await session.commit()

        entity = await example_repo.read(sample_entity.id)

        assert isinstance(entity, ExampleEntity)

        await example_repo.delete(sample_entity.id)
        await session.commit()

        entity = await example_repo.read(sample_entity.id)

        assert entity is None
