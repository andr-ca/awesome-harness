import pytest

from discount import calculate_discount


def test_normal_discount():
    assert calculate_discount(100, 0.1) == 90


def test_edge_zero_discount():
    assert calculate_discount(100, 0) == 100


def test_edge_full_discount():
    assert calculate_discount(100, 1.0) == 0


def test_edge_zero_price():
    assert calculate_discount(0, 0.5) == 0


def test_edge_negative_price_raises():
    with pytest.raises(ValueError):
        calculate_discount(-1, 0.1)


def test_edge_negative_rate_raises():
    with pytest.raises(ValueError):
        calculate_discount(100, -0.1)


def test_edge_rate_over_one_raises():
    with pytest.raises(ValueError):
        calculate_discount(100, 1.5)
