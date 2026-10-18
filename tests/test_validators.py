import pytest

from services.validators import normalize_full_name, normalize_phone


@pytest.mark.parametrize("raw, expected", [
    ("иван петров", "Иван Петров"),
    ("  Анна-Мария   Иванова ", "Анна-Мария Иванова"),
    ("John Smith", "John Smith"),
    ("Пётр Ильич Чайковский", "Пётр Ильич Чайковский"),
])
def test_valid_names(raw, expected):
    assert normalize_full_name(raw) == expected


@pytest.mark.parametrize("raw", ["Иван", "", "Иван 123", "Иван Петров!", "Иван -", "R2D2 Петров"])
def test_invalid_names(raw):
    assert normalize_full_name(raw) is None


@pytest.mark.parametrize("raw", [
    "+7 912 345-67-89", "8 (912) 345 67 89", "79123456789", "89123456789", "9123456789",
])
def test_valid_phones(raw):
    assert normalize_phone(raw) == "+79123456789"


@pytest.mark.parametrize("raw", [
    "12345", "+1 202 555 0100", "+7 812 123-45-67", "8912345678a", "+7912345678901", "",
])
def test_invalid_phones(raw):
    assert normalize_phone(raw) is None
