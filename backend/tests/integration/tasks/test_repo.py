import pytest

from src.tasks.infra.repos import SqlTaskRepository


@pytest.fixture
def task_repo(session):
    return SqlTaskRepository(session)


@pytest.mark.asyncio
class TestGetNextSequence:

    async def test_first_call_returns_one(self, task_repo):
        """
        При первом вызове должна возвращаться единица
        """

        sequence = await task_repo.get_next_sequence()
        assert sequence == 1

    async def test_sequential_calls_should_increment_sequence(self, task_repo):
        """
        Последовательные вызовы должны увеличивать последовательность
        """

        first = await task_repo.get_next_sequence()
        assert first == 1

        second = await task_repo.get_next_sequence()
        assert second == 2  # noqa: PLR2004

        third = await task_repo.get_next_sequence()
        assert third == 3  # noqa: PLR2004
