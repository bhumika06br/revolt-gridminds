"""Small helpers for checking data that comes from the frontend."""
import math


def require_number(value, name, min_value=None, max_value=None):
    """Check that `value` is a real number. Returns it as a float.

    Raises ValueError with a clear message if it is not.
    """
    # In Python, True/False count as numbers (True == 1), so reject them on purpose.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"'{name}' must be a number")
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"'{name}' must be a finite number")
    if min_value is not None and value < min_value:
        raise ValueError(f"'{name}' must be at least {min_value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"'{name}' must be at most {max_value}")
    return float(value)
