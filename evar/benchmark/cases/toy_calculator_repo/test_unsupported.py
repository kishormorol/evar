import pytest

from calculator import divide


def test_divide_by_two_raises_zero_division_error():
    with pytest.raises(ZeroDivisionError):
        divide(10, 2)
