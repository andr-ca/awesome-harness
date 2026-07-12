def average_price(prices):
    """Return the mean of prices, or 0.0 for an empty list."""
    if not prices:
        return 0.0
    return sum(prices) / len(prices)
