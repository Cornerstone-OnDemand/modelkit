import pytest

from modelkit.core.model import Model


async def _identity(x):
    return x


async def _double(x):
    return [y * 2 for y in x]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "func,items,batch_size,expected",
    [
        (_identity, [], None, []),
        (_identity, [1], None, [1]),
        (_identity, list(range(2048)), None, list(range(2048))),
        (_double, [1, 2, 3], None, [2, 4, 6]),
        (_double, [1, 2, 3], 1, [2, 4, 6]),
        (_double, [1, 2, 3], 128, [2, 4, 6]),
    ],
)
async def test_identitybatch_batch_process(
    func, items, batch_size, expected, monkeypatch
):

    m = Model()
    monkeypatch.setattr(m, "_predict_batch", func)
    if batch_size:
        assert await m._predict_by_batch(items, batch_size=batch_size) == expected
    else:
        assert await m._predict_by_batch(items) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "items,batch_size,expected_steps",
    [
        ([], 1, 0),
        (list(range(3)), 1, 3),
        (list(range(3)), 64, 1),
        (list(range(128)), 1, 128),
        (list(range(128)), 64, 2),
        (list(range(128)), 63, 3),
    ],
)
async def test_callback_batch_process(items, batch_size, expected_steps, monkeypatch):
    steps = 0

    async def func(items):
        return [item + 1 for item in items]

    def callback(batch_step, batch_items, batch_results):
        nonlocal steps
        nonlocal items
        assert items[batch_step : batch_step + batch_size] == batch_items
        steps += 1

    m = Model()
    monkeypatch.setattr(m, "_predict_batch", func)
    await m._predict_by_batch(items, batch_size=batch_size, callback=callback)
    assert steps == expected_steps
