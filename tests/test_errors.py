import pytest

from modelkit.core.model import AsyncModel, Model


class CustomError(BaseException):
    pass


class OKModel(Model):
    def _predict(self, item):
        return self.model_dependencies["error_model"].predict(item)


class ErrorModel(Model):
    def _predict(self, item):
        raise CustomError("something went wrong")


class ErrorBatchModel(Model):
    def _predict_batch(self, item):
        raise CustomError("something went wrong")


@pytest.mark.parametrize("model", [ErrorModel(), ErrorBatchModel()])
def test_prediction_error(model):
    with pytest.raises(CustomError) as excinfo:
        model.predict({})
    assert len(excinfo.traceback) <= 3

    with pytest.raises(CustomError) as excinfo:
        model.predict_batch([{}])
    assert len(excinfo.traceback) <= 3

    with pytest.raises(CustomError) as excinfo:
        next(model.predict_gen(iter(({},))))
    assert len(excinfo.traceback) <= 3


def test_prediction_error_composition():

    mm = OKModel(model_dependencies={"error_model": ErrorModel()})
    mm.load()

    with pytest.raises(CustomError) as excinfo:
        mm.predict({})
    assert len(excinfo.traceback) <= 4

    with pytest.raises(CustomError) as excinfo:
        mm.predict_batch([{}])
    assert len(excinfo.traceback) <= 4

    with pytest.raises(CustomError) as excinfo:
        next(mm.predict_gen(iter(({},))))
    assert len(excinfo.traceback) <= 4


@pytest.mark.parametrize("model", [ErrorModel(), ErrorBatchModel()])
def test_prediction_error_complex_tb(monkeypatch, model):
    monkeypatch.setenv("MODELKIT_ENABLE_SIMPLE_TRACEBACK", False)
    with pytest.raises(CustomError) as excinfo:
        model.predict({})
    assert len(excinfo.traceback) > 3

    with pytest.raises(CustomError) as excinfo:
        model.predict_batch([{}])
    assert len(excinfo.traceback) > 3

    with pytest.raises(CustomError) as excinfo:
        next(model.predict_gen(iter(({},))))
    assert len(excinfo.traceback) > 3


class AsyncOKModel(AsyncModel):
    async def _predict(self, item):
        return self.model_dependencies["error_model"].predict(item)


class AsyncErrorModel(AsyncModel):
    async def _predict(self, item):
        raise CustomError("something went wrong")


class AsyncErrorBatchModel(AsyncModel):
    async def _predict_batch(self, item):
        raise CustomError("something went wrong")


@pytest.mark.asyncio
@pytest.mark.parametrize("model", [AsyncErrorModel(), AsyncErrorBatchModel()])
async def test_prediction_error_async(model):
    with pytest.raises(CustomError) as excinfo:
        await model.predict({})
    assert len(excinfo.traceback) <= 3

    with pytest.raises(CustomError) as excinfo:
        await model.predict_batch([{}])
    assert len(excinfo.traceback) <= 3

    with pytest.raises(CustomError) as excinfo:
        async for x in model.predict_gen(iter(({},))):
            pass
    assert len(excinfo.traceback) <= 3


@pytest.mark.asyncio
@pytest.mark.parametrize("model", [AsyncErrorModel(), AsyncErrorBatchModel()])
async def test_prediction_error_complex_tb_async(monkeypatch, model):
    monkeypatch.setenv("MODELKIT_ENABLE_SIMPLE_TRACEBACK", False)
    with pytest.raises(CustomError) as excinfo:
        await model.predict({})
    assert len(excinfo.traceback) > 3

    with pytest.raises(CustomError) as excinfo:
        await model.predict_batch([{}])
    assert len(excinfo.traceback) > 3

    with pytest.raises(CustomError) as excinfo:
        async for x in model.predict_gen(iter(({},))):
            pass
    assert len(excinfo.traceback) > 3


def test_internal_error(monkeypatch):
    m = OKModel()

    class CustomError(BaseException):
        pass

    def _buggy_predict_cache_items(*args, **kwargs):
        raise CustomError
        yield None

    monkeypatch.setattr(m, "_predict_cache_items", _buggy_predict_cache_items)
    with pytest.raises(CustomError):
        m({})

    with pytest.raises(CustomError):
        m.predict({})

    with pytest.raises(CustomError):
        m.predict_batch([{}])

    with pytest.raises(CustomError):
        for _ in m.predict_gen([{}]):
            pass


@pytest.mark.asyncio
async def test_internal_error_async(monkeypatch):
    m = AsyncOKModel()

    class CustomError(BaseException):
        pass

    async def _buggy_predict_cache_items(*args, **kwargs):
        raise CustomError
        yield None

    monkeypatch.setattr(m, "_predict_cache_items", _buggy_predict_cache_items)
    with pytest.raises(CustomError):
        await m({})

    with pytest.raises(CustomError):
        await m.predict({})

    with pytest.raises(CustomError):
        await m.predict_batch([{}])

    with pytest.raises(CustomError):
        async for _ in m.predict_gen(iter(({},))):
            pass
