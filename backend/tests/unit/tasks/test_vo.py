import pytest

from src.projects.domain.vo import ProjectKey
from src.tasks.domain.vo import TaskNumber
from src.tickets.domain.vo import TicketNumber


class TestTaskNumber:

    def test_create_with_project_key(self):
        """
        Создание номера по ключу проекта
        """

        sequence = 5
        project_key = ProjectKey("DEV")
        number = TaskNumber.create(sequence=sequence, project_key=project_key)

        assert number.value == "DEV-005"
        assert f"{number}" == "DEV-005"
        assert number.prefix == f"{project_key}"
        assert number.sequence == sequence
        assert number.is_internal is False

    def test_create_with_ticket_number(self):
        """
        Создание по номеру тикета
        """

        sequence = 12
        ticket_number = TicketNumber("PRJ-26-00000007")
        number = TaskNumber.create(sequence=sequence, ticket_number=ticket_number)
        assert f"{number}" == "PRJ-26-00000007-012"
        assert number.prefix == "PRJ-26-00000007"
        assert number.sequence == sequence
        assert number.is_internal is False

    def test_create_without_context(self):
        """
        Создание автономной задачи без дополнительного контекста
        """

        sequence = 999
        number = TaskNumber.create(sequence=sequence)

        assert f"{number}" == "TASK-999"

    @pytest.mark.parametrize(
        "valid_str",
        [
            "TASK-001",
            "DEV-123",
            "PR-1",
            "TICKET-99-00000001-001",
        ],
    )
    def test_valid_format_strings(self, valid_str):
        assert TaskNumber.is_valid_format(valid_str) is True
