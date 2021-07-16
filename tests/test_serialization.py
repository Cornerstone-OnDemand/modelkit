import numpy as np
import pytest

from modelkit.utils.serialization import safe_np_dump


@pytest.mark.parametrize(
    "value, result",
    [
        (np.arange(4), [0, 1, 2, 3]),
        (np.zeros((1,))[0], 0),
        (np.zeros((1,), dtype=int)[0], 0),
        (1, 1),
    ],
)
def test_safe_np_dump(value, result):
    assert safe_np_dump(value) == result
