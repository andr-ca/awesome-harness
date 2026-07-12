def calculate_discount(price, discount_rate):
    """Return price after applying discount_rate.

    Raises ValueError for a negative price or a discount_rate outside
    [0, 1].
    """
    if price < 0:
        raise ValueError("price must not be negative")
    if not 0 <= discount_rate <= 1:
        raise ValueError("discount_rate must be between 0 and 1")
    return price - (price * discount_rate)
