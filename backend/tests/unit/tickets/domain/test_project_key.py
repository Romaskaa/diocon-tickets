import pytest

from src.tickets.domain.vo import ProjectKey


class TestProjectKey:

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("prj", "PRJ"),
            ("  mOb_App  ", "MOBAPP"),
            ("Backend1", "BACKEND1"),
            ("A1", "A1"),
            ("A_" * 5, "A" * 5),
            ("_PROJ", "PROJ"),
            ("PROJ.", "PROJ"),
            ("PROJ-1", "PROJ1"),
            ("PRO J", "PROJ"),
            ("project", "PROJECT"),
        ],
    )
    def test_should_create_valid_key_and_normalize(self, raw, expected):
        key = ProjectKey(raw)
        assert key.value == expected
        assert str(key) == expected
        assert repr(key) == f"ProjectKey('{expected}')"

    @pytest.mark.parametrize(
        "invalid_key",
        [
            "A",  # слишком короткий (1 символ)
            "A" * 11,  # слишком длинный (11 символов)
            "1PROJ",  # начинается с цифры
            "абвгдежзикл",  # 11 символов
        ],
    )
    def test_should_raise_error_for_invalid_key(self, invalid_key):
        with pytest.raises(ValueError, match="Invalid project key format"):
            ProjectKey(invalid_key)

    def test_should_raise_error_for_empty_string(self):
        with pytest.raises(ValueError, match="Project key cannot be empty"):
            ProjectKey("")

    def test_should_strip_whitespace_and_uppercase(self):
        key = ProjectKey("   test_key   ")
        assert key.value == "TESTKEY"

    def test_should_accept_underscore_and_digits(self):
        key = ProjectKey("PROJ_123")
        assert key.value == "PROJ123"
