import pytest

from src.staffing.domain.vo import Skill, SkillLevel


def test_skill_create_success():
    """
    Навык хранит данные для подбора сотрудника.
    """
    skill = Skill(name="PostgreSQL", level=SkillLevel.MIDDLE, years_experience=3)

    assert skill.name == "PostgreSQL"
    assert skill.level == SkillLevel.MIDDLE
    assert skill.years_experience == 3


@pytest.mark.parametrize("name", ["", " "])
def test_skill_empty_name_raises_value_error(name):
    """
    Название навыка обязательно для подбора.
    """

    with pytest.raises(ValueError, match="Skill name cannot be empty"):
        Skill(name=name, level=SkillLevel.JUNIOR, years_experience=0)


def test_skill_short_name_raises_value_error():
    """
    Название навыка должно быть достаточно длинным.
    """

    with pytest.raises(ValueError, match="Skill name must be between"):
        Skill(name="A", level=SkillLevel.JUNIOR, years_experience=0)


def test_skill_negative_years_experience_raises_value_error():
    """
    Опыт по навыку не может быть отрицательным.
    """

    with pytest.raises(ValueError, match="Skill years experience cannot be negative"):
        Skill(name="Python", level=SkillLevel.JUNIOR, years_experience=-1)
