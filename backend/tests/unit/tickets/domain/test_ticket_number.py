import pytest

from src.shared.utils.text import get_latin_slug
from src.shared.utils.time import current_datetime
from src.tickets.domain.vo import ProjectKey, TicketNumber


@pytest.fixture
def valid_project_key():
    return ProjectKey("PRJ123")


class TestCreateInternal:
    """
    Тесты генерации номера для внутреннего тикета
    """

    def test_create_internal_ticket_number(self):
        total_tickets = 0
        number = TicketNumber.create(total_tickets)

        assert isinstance(number, TicketNumber)
        assert number.value.startswith("INT-")
        assert number.is_internal is True
        assert number.prefix == "INT"
        assert len(number.value) == 3 + 1 + 2 + 1 + 8
        assert number.year_short == current_datetime().year % 100

    def test_create_internal_ticket_with_different_counts(self):
        number1 = TicketNumber.create(0)
        number2 = TicketNumber.create(1)
        number3 = TicketNumber.create(999)

        assert number1.sequence == "00000001"
        assert number2.sequence == "00000002"
        assert number3.sequence == "00001000"

    def test_create_internal_negative_total_raises_error(self):
        with pytest.raises(ValueError, match="Total tickets cannot be negative"):
            TicketNumber.create(-1)


class TestCreateForCounterparty:
    """
    Тесты генерации номера для тикета созданного в рамках контрагента
    """

    @pytest.mark.parametrize(
        ("russian_name", "excepted_number"),
        [
            ("Яндекс Такси", "IANDEKSTAK-26-00000006"),
            ("Ромашка", "ROMASHKA-26-00000006")
        ],
    )
    def test_create_with_russian_name(self, russian_name, excepted_number):
        total_tickets = 5
        number = TicketNumber.create(total_tickets, counterparty_name=russian_name)

        assert f"{number}" == excepted_number
        assert number.is_internal is False

    def test_create_with_short_name(self):
        total_tickets = 0
        number = TicketNumber.create(total_tickets, counterparty_name="Я")

        assert number.prefix == "IA"

    def test_create_with_long_name(self):
        total_tickets = 0
        long_name = "Общество с ограниченной ответственностью Ромашка"
        number = TicketNumber.create(total_tickets, counterparty_name=long_name)

        excepted_prefix = get_latin_slug(long_name)
        excepted_prefix = excepted_prefix[:10].upper()

        assert number.prefix == excepted_prefix
        assert number.prefix.isalnum()
        assert all(char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for char in number.prefix)

    def test_create_with_english_name(self):
        total_tickets = 0
        ticket_number = TicketNumber.create(total_tickets, counterparty_name="Acme Corp")

        assert ticket_number.prefix == "ACMECORP"

    def test_create_with_mixed_language_and_special_chars(self):
        total_tickets = 0
        number = TicketNumber.create(total_tickets, counterparty_name="ООО Яндекс.Такси")

        assert number.prefix.isalnum()
        assert number.prefix.startswith("OOO")

    def test_create_with_umlauts(self):
        total_tickets = 0
        number = TicketNumber.create(
            total_tickets, counterparty_name="Müller & Söhne"
        )

        assert number.prefix.isalnum()
        assert "MULLER" in number.prefix or "MULLERS" in number.prefix

    def test_create_with_empty_name(self):
        with pytest.raises(ValueError, match="Invalid ticket number format"):
            TicketNumber.create(0, counterparty_name="")


class TestCreateForProject:
    """
    Тесты генерации номера для тикета в рамках проекта
    """

    def test_create_with_valid_key(self, valid_project_key):
        total_tickets = 10
        number = TicketNumber.create(total_tickets, project_key=valid_project_key)

        assert number.prefix == "PRJ123"
        assert number.value.startswith("PRJ123-")
        assert number.sequence == "00000011"
        assert number.is_internal is False
        assert f"{number}" == "PRJ123-26-00000011"


class TestFormatValidation:
    """
    Тесты для валидации формата
    """

    def test_invalid_number_format_raises_error(self):

        # Отсутсвует 8-разрядный номер
        with pytest.raises(ValueError, match="Invalid ticket number format"):
            TicketNumber(value="ROMASHKA-26")

        # Неверная длина последовательности (7 цифр)
        with pytest.raises(ValueError, match="Invalid ticket number format"):
            TicketNumber(value="ROMASHKA-26-1234567")

        # Год из 4 цифр
        with pytest.raises(ValueError, match="Invalid ticket number format"):
            TicketNumber(value="ROMASHKA-2026-12345678")

        # Префикс с недопустимыми символами (кириллица)
        with pytest.raises(ValueError, match="Invalid ticket number format"):
            TicketNumber(value="РОМ-26-12345678")

        # Префикс пустой
        with pytest.raises(ValueError, match="Invalid ticket number format"):
            TicketNumber(value="-26-12345678")

        # Пустая строка
        with pytest.raises(ValueError, match="Ticket number cannot be empty"):
            TicketNumber(value="")


def test_create_with_project_and_counterparty_raises_error(valid_project_key):
    with pytest.raises(
            ValueError,
            match="Only one of the project key or counterparty name must be specified"
    ):
        TicketNumber.create(123, project_key=valid_project_key, counterparty_name="Ромашка")


def test_sequence_overflow_protection():
    max_tickets = 99_999_999
    number = TicketNumber.create(max_tickets - 1)
    assert number.sequence == "99999999"

    with pytest.raises(ValueError, match="Invalid ticket number format"):
        TicketNumber.create(max_tickets)


def test_cannot_be_empty():
    with pytest.raises(ValueError, match="cannot be empty"):
        TicketNumber("   ")


@pytest.mark.parametrize(
    "wrong_number",
    [
        "WEB-25_12345678",  # Неправильный разделитель
        "РОМАШКА-26-00000001",  # Русские символы
        "ROMASHKAROMASHKA-26-12345678",  # Длинный префикс
        "WEB-FG-123Gj678"  # Буквы в номере
    ]
)
def test_invalid_number_format(wrong_number):
    with pytest.raises(ValueError, match="Invalid ticket number format"):
        TicketNumber(wrong_number)
