import pytest

from modelkit.core.model import Model


def _identity(x):
    return x


def _double(x):
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
def test_identitybatch_batch_process(func, items, batch_size, expected, monkeypatch):

    m = Model()
    monkeypatch.setattr(m, "_predict_batch", func)
    if batch_size:
        assert m.predict_batch(items, batch_size=batch_size) == expected
    else:
        assert m.predict_batch(items) == expected


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
def test_callback_batch_process(items, batch_size, expected_steps, monkeypatch):
    steps = 0

    def func(items):
        return [item + 1 for item in items]

    def _callback(batch_step, batch_items, batch_results):
        nonlocal steps
        nonlocal items
        assert items[batch_step : batch_step + batch_size] == batch_items
        steps += 1

    m = Model()
    monkeypatch.setattr(m, "_predict_batch", func)
    m.predict_batch(items, batch_size=batch_size, _callback=_callback)
    m.predict_gen(items, batch_size=batch_size, _callback=_callback)
    assert steps == expected_steps


def _do_gen_test(m, batch_size, n_items):
    def item_iterator():
        for x in range(n_items):
            yield x

    for value, position_in_batch, batch_len in m.predict_gen(
        item_iterator(), batch_size=batch_size
    ):
        assert position_in_batch == value % batch_size
        if value < (n_items // batch_size) * batch_size:
            assert batch_len == batch_size
        else:
            assert batch_len == n_items - n_items // batch_size * batch_size


def test_predict_gen():
    class GeneratorTestModel(Model):
        def _predict_batch(self, items):
            # returns the size of the batch
            return [
                (item, position_in_batch, len(items))
                for (position_in_batch, item) in enumerate(items)
            ]

    m = GeneratorTestModel()

    _do_gen_test(m, 16, 66)
    _do_gen_test(m, 10, 8)
    _do_gen_test(m, 100, 5)
