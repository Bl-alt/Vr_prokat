import pytest

from config import DAILY, HOURLY, WEEKLY
from services.pricing import calc_price, plural, tariff_label


@pytest.mark.parametrize("tariff, duration, price", [
    (HOURLY, 1, 500), (HOURLY, 5, 2500), (HOURLY, 12, 6000),
    (DAILY, 1, 2500), (DAILY, 2, 5000),
    (WEEKLY, 7, 7000),
])
def test_prices(tariff, duration, price):
    assert calc_price(tariff, duration) == price


@pytest.mark.parametrize("tariff, duration", [
    (HOURLY, 0), (HOURLY, 13), (DAILY, 3), (WEEKLY, 1), ("monthly", 30),
])
def test_invalid_tariffs(tariff, duration):
    with pytest.raises(ValueError):
        calc_price(tariff, duration)


def test_labels():
    assert tariff_label(HOURLY, 1) == "1 час"
    assert tariff_label(HOURLY, 3) == "3 часа"
    assert tariff_label(HOURLY, 11) == "11 часов"
    assert tariff_label(DAILY, 1) == "1 сутки"
    assert tariff_label(DAILY, 2) == "2 суток"
    assert plural(21, "a", "b", "c") == "a"
