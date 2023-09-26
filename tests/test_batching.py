import asyncio

import pytest

from modelkit.core.model import AsyncModel, Model


def _identity(x):
    return x


def _double(x):
    return [y * 2 for y in x]


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
    class SomeModel(Model):
        def _predict(self, item):
            return item

    m = SomeModel()
    monkeypatch.setattr(m, "_predict_batch", func)
    if batch_size:
        assert m.predict_batch(items, batch_size=batch_size) == expected
    else:
        assert m.predict_batch(items) == expected


CALLBACK_TEST_CASES = [
    ([], 1, 0, 0),
    (list(range(3)), 1, 3, 3),
    (list(range(3)), 64, 1, 1),
    (list(range(128)), 1, 128, 128),
    (list(range(128)), 64, 2, 2),
    (list(range(128)), 63, 3, 3),
    (list(range(128)), None, 1, 128),
]


def callback_func(items):
    return [item + 1 for item in items]


class SomeModel(Model):
    def _predict_batch(self, items, **_):
        return callback_func(items)


@pytest.mark.parametrize(
    "items,batch_size,expected_steps,expected_steps_gen",
    CALLBACK_TEST_CASES,
)
def test_callback_batch_process(items, batch_size, expected_steps, expected_steps_gen):
    steps = 0

    def _callback(batch_step, batch_items, batch_results):
        nonlocal steps
        nonlocal items
        if batch_size:
            assert items[batch_step : batch_step + batch_size] == batch_items
        assert callback_func(batch_items) == batch_results
        steps += 1

    m = SomeModel()
    m.predict_batch(items, batch_size=batch_size, _callback=_callback)
    assert steps == expected_steps

    steps = 0

    def _callback_gen(batch_step, batch_items, batch_results):
        nonlocal steps
        steps += 1
        if batch_size:
            assert items[batch_step : batch_step + batch_size] == batch_items
        else:
            assert len(batch_items) == 1
        assert callback_func(batch_items) == batch_results

    list(m.predict_gen(iter(items), batch_size=batch_size, _callback=_callback_gen))
    assert steps == expected_steps_gen


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "items,batch_size,expected_steps,expected_steps_gen",
    CALLBACK_TEST_CASES,
)
async def test_callback_batch_process_async(
    items, batch_size, expected_steps, expected_steps_gen
):
    steps = 0

    class SomeAsyncModel(AsyncModel):
        async def _predict_batch(self, items, **_):
            await asyncio.sleep(0)
            return callback_func(items)

    def _callback(batch_step, batch_items, batch_results):
        nonlocal steps
        nonlocal items
        if batch_size:
            assert items[batch_step : batch_step + batch_size] == batch_items
        assert callback_func(batch_items) == batch_results
        steps += 1

    m = SomeAsyncModel()
    await m.predict_batch(items, batch_size=batch_size, _callback=_callback)
    assert steps == expected_steps

    steps = 0

    def _callback_gen(batch_step, batch_items, batch_results):
        nonlocal steps
        steps += 1
        if batch_size:
            assert items[batch_step : batch_step + batch_size] == batch_items
        else:
            assert len(batch_items) == 1
        assert callback_func(batch_items) == batch_results

    async for _ in m.predict_gen(
        iter(items), batch_size=batch_size, _callback=_callback_gen
    ):
        pass
    assert steps == expected_steps_gen


def _do_gen_test(m, batch_size, n_items):
    def item_iterator():
        yield from range(n_items)

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


async def _do_gen_test_async(m, batch_size, n_items):
    def item_iterator():
        yield from range(n_items)

    async for value, position_in_batch, batch_len in m.predict_gen(
        item_iterator(), batch_size=batch_size
    ):
        assert position_in_batch == value % batch_size
        if value < (n_items // batch_size) * batch_size:
            assert batch_len == batch_size
        else:
            assert batch_len == n_items - n_items // batch_size * batch_size


@pytest.mark.asyncio
async def test_predict_gen_async():
    class AsyncGeneratorTestModel(AsyncModel):
        async def _predict_batch(self, items):
            await asyncio.sleep(0)
            # returns the size of the batch
            return [
                (item, position_in_batch, len(items))
                for (position_in_batch, item) in enumerate(items)
            ]

    m = AsyncGeneratorTestModel()

    await _do_gen_test_async(m, 16, 66)
    await _do_gen_test_async(m, 10, 8)
    await _do_gen_test_async(m, 100, 5)


def test_generator_exit_callback():
    steps = 0
    batch_size = 32
    batch_break = int(batch_size / 2)

    def _callback(batch_step, batch_items, batch_results):
        nonlocal steps
        # batch_items' length equals batch size by definition
        assert len(batch_items) == batch_size
        # however, we just saw mid-batch size items
        assert len(batch_results) == batch_break
        # (despite batch_size items we actually computed)
        assert callback_func(batch_items)[:batch_break] == batch_results
        # we break during the first batch, at mid-batch size
        assert batch_step < 1
        steps += 1

    m = SomeModel()
    for i, _prediction in enumerate(
        m.predict_gen(range(100), _callback=_callback, batch_size=batch_size)
    ):
        if i + 1 == batch_break:
            break
    assert steps == 1
