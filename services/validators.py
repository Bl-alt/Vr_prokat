"""Проверка и нормализация пользовательского ввода."""
import re

_NAME_PART = re.compile(r"^[^\W\d_]+(?:-[^\W\d_]+)*$")  # буквы, допускается дефис: Анна-Мария


def normalize_full_name(raw: str) -> str | None:
    """Возвращает «Имя Фамилия» с заглавными буквами или None, если ввод некорректен.

    Требования: минимум два слова, только буквы (двойные имена через дефис допустимы).
    """
    parts = raw.split()
    if len(parts) < 2 or len(" ".join(parts)) > 100:
        return None
    if not all(_NAME_PART.match(p) for p in parts):
        return None
    return " ".join("-".join(s.capitalize() for s in p.split("-")) for p in parts)


def normalize_phone(raw: str) -> str | None:
    """Приводит российский мобильный номер к виду +7XXXXXXXXXX или возвращает None.

    Принимает: +7 912 345-67-89, 8 (912) 345 67 89, 79123456789, 9123456789.
    """
    raw = raw.strip()
    if not re.fullmatch(r"\+?[\d\s\-()]+", raw):
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        digits = "7" + digits
    elif len(digits) == 11 and digits[0] in "78":
        digits = "7" + digits[1:]
    else:
        return None
    if digits[1] != "9":  # российские мобильные начинаются на +79
        return None
    return "+" + digits
