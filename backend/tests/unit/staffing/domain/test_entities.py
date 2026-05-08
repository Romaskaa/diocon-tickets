from datetime import time
from uuid import uuid4

import pytest

from src.staffing.domain.entities import Employee, SupportLine
from src.staffing.domain.vo import Skill, SkillLevel, SupportLineLevel


@pytest.fixture
def python_skill():
    return Skill(name="Python", level=SkillLevel.SENIOR, years_experience=5)


def test_employee_add_skill_success(python_skill):
    """
    Сотруднику можно добавить новый навык для будущего подбора исполнителя.
    """
    employee = Employee(user_id=uuid4())

    employee.add_skill(python_skill)

    assert employee.skills == [python_skill]


def test_employee_add_duplicate_skill_raises_value_error(python_skill):
    """
    У сотрудника не может быть двух навыков с одинаковым названием.
    """
    employee = Employee(user_id=uuid4(), skills=[python_skill])

    with pytest.raises(ValueError, match="Skill Python already exists"):
        employee.add_skill(
            Skill(name="Python", level=SkillLevel.EXPERT, years_experience=7)
        )


def test_employee_load_cannot_go_below_zero():
    """
    Счетчик нагрузки сотрудника не уходит ниже нуля.
    """
    employee = Employee(user_id=uuid4())

    employee.decrease_load()

    assert employee.current_load == 0


def test_employee_increase_and_decrease_load_success():
    """
    Счетчик нагрузки отражает активные назначения.
    """
    employee = Employee(user_id=uuid4())

    employee.increase_load()
    employee.increase_load()
    employee.decrease_load()

    assert employee.current_load == 1


def test_support_line_defaults_are_assignment_ready():
    """
    Линия поддержки по умолчанию готова к автоназначению.
    """
    support_line = SupportLine(level=SupportLineLevel.L1, name="Первая линия")

    assert support_line.level == SupportLineLevel.L1
    assert support_line.auto_assignment_enabled is True
    assert support_line.ai_assignment_threshold == 0.75
    assert support_line.is_default is False


def test_employee_working_hours_are_stored():
    """
    Профиль сотрудника хранит рабочие часы для будущей проверки доступности.
    """
    employee = Employee(
        user_id=uuid4(),
        working_hours_start=time(hour=9),
        working_hours_end=time(hour=18),
    )

    assert employee.working_hours_start == time(hour=9)
    assert employee.working_hours_end == time(hour=18)
