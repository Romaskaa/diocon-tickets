# Тесты для доменного примитива FullName (ФИО)

import pytest

from src.iam.domain.vo import FullName


@pytest.mark.parametrize(
    ("input_str", "expected_normalized"),
    [
        ("иван иванов", "Иван Иванов"),
        ("ИВАН ИВАНОВИЧ ИВАНОВ", "Иван Иванович Иванов"),
        ("  петр   петрович   петров  ", "Петр Петрович Петров"),
        ("Anna-Maria O'Connor", "Anna-Maria O'Connor"),
        ("Мария-Анна Сергеевна-Кузнецова", "Мария-Анна Сергеевна-Кузнецова"),
        ("john doe", "John Doe"),
    ],
)
def test_valid_full_names_are_normalized(input_str: str, expected_normalized: str):
    """Тестирован нормализации валидно введённого ФИО"""

    full_name = FullName(input_str)
    assert full_name == expected_normalized


@pytest.mark.parametrize(
    ("invalid_input", "expected_error_substring"),
    [
        ("", "cannot be empty"),
        ("   ", "cannot be empty"),
        ("Иван", "at least first and last name"),
        ("И", "at least first and last name"),
        ("Иван123 Иванов", "Invalid characters"),
        ("Иван @ Иванов", "Invalid characters"),
        ("Иван Иванов!", "Invalid characters"),
        ("Иван  Иванов  123", "Invalid characters"),
        (155 * "А" + "Андрей Андреевич", "Full name cannot be longer than 155 characters"),
    ],
)
def test_invalid_names_raise_error(invalid_input, expected_error_substring):
    with pytest.raises(ValueError) as exc:  # noqa: PT011
        FullName(invalid_input)

    assert expected_error_substring.lower() in str(exc.value).lower()


def test_equality_with_string():
    full_name = FullName("Анна Сергеевна Смирнова")

    incorrect_value = 123

    assert full_name == "Анна Сергеевна Смирнова"
    assert full_name != "  анна   сергеевна  смирнова  "
    assert full_name == "Анна Сергеевна Смирнова"
    assert full_name != "Анна Смирнова"
    assert full_name != "Другая Анна Смирнова"
    assert full_name != incorrect_value
    assert full_name != ["Анна", "Смирнова"]


def test_hashable_and_set_behavior():
    full_names = {
        FullName("Иван Иванов"),
        FullName("иван иванов"),
        FullName("  Иван   Иванов  "),
        FullName("Петр Петров"),
    }

    excepted_length = 2
    assert len(full_names) == excepted_length
    assert FullName("Иван Иванов") in full_names


def test_parts_properties():
    full_name = FullName("Екатерина Владимировна Соколова")

    assert full_name.first_name == "Екатерина"
    assert full_name.middle_name == "Владимировна"
    assert full_name.last_name == "Соколова"

    full_name_without_middle_name = FullName("Сергей Морозов")
    assert full_name_without_middle_name.first_name == "Сергей"
    assert full_name_without_middle_name.middle_name is None
    assert full_name_without_middle_name.last_name == "Морозов"


def test_minimal_name_two_parts():
    name = FullName("Ли Чжан")
    assert name == "Ли Чжан"
    assert name.middle_name is None


def test_multiple_middle_names():
    name = FullName("Александр Сергеевич Пушкин-Блудов")
    assert name.first_name == "Александр"
    assert name.middle_name == "Сергеевич"
    assert name.last_name == "Пушкин-Блудов"


def test_apostrophe_and_hyphen_allowed():
    name = FullName("O'Brien O'Malley")
    assert str(name) == "O'Brien O'Malley"


def test_repr():
    name = FullName("Тест Тестович Тестов")
    assert repr(name) == "FullName('Тест Тестович Тестов')"
