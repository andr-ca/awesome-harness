from stats import average_price


def test_normal_average():
    assert average_price([10.0, 20.0, 30.0]) == 20.0


def test_edge_empty_list_returns_zero():
    assert average_price([]) == 0.0


def test_edge_single_item():
    assert average_price([5.0]) == 5.0


def test_edge_negative_prices():
    assert average_price([-10.0, 10.0]) == 0.0
