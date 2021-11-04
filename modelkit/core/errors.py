import functools
import inspect
import os
import traceback
import types
from typing import Any, Callable, Optional, TypeVar, cast

import pydantic

PYDANTIC_ERROR_TRUNCATION = 20


class ModelsNotFound(Exception):
    pass


class PredictionError(Exception):
    def __init__(self, exc):
        self.exc = exc


class ModelkitDataValidationException(Exception):
    def __init__(
        self,
        model_identifier: str,
        pydantic_exc: Optional[pydantic.error_wrappers.ValidationError] = None,
        error_str: str = "Data validation error in model",
    ):
        pydantic_exc_output = ""
        if pydantic_exc:
            exc_lines = str(pydantic_exc).split("\n")
            if len(exc_lines) > PYDANTIC_ERROR_TRUNCATION:
                pydantic_exc_output += "Pydantic error message "
                pydantic_exc_output += (
                    f"(truncated to {PYDANTIC_ERROR_TRUNCATION} lines):\n"
                )
                pydantic_exc_output += "\n".join(exc_lines[:PYDANTIC_ERROR_TRUNCATION])
                pydantic_exc_output += (
                    f"\n({len(exc_lines)-PYDANTIC_ERROR_TRUNCATION} lines truncated)"
                )
            else:
                pydantic_exc_output += "Pydantic error message:\n"
                pydantic_exc_output += str(pydantic_exc)

        super().__init__(f"{error_str} `{model_identifier}`.\n" + pydantic_exc_output)


class ValidationInitializationException(
    ModelkitDataValidationException
):  # pragma: no cover
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            error_str="Exception when setting up pydantic validation models",
            pydantic_exc=kwargs.pop("pydantic_exc"),
        )


class ReturnValueValidationException(ModelkitDataValidationException):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            error_str="Return value validation error when calling model",
            pydantic_exc=kwargs.pop("pydantic_exc"),
        )


class ItemValidationException(ModelkitDataValidationException):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            error_str="Predict item validation error when calling model",
            pydantic_exc=kwargs.pop("pydantic_exc"),
        )


def is_modelkit_internal_frame(frame: types.FrameType):
    """
    Guess whether the frame originates from a submodule of `modelkit`
    """
    try:
        mod = inspect.getmodule(frame)
        if mod:
            frame_package = __package__.split(".")[0]
            return frame_package == "modelkit"
    except BaseException:
        pass
    return False


def strip_modelkit_traceback_frames(exc: BaseException):
    """
    Walk the traceback and remove frames that originate from within modelkit
    Return an exception with the filtered traceback
    """
    tb = None
    for tb_frame, _ in reversed(list(traceback.walk_tb(exc.__traceback__))):
        if not is_modelkit_internal_frame(tb_frame):
            tb = types.TracebackType(tb, tb_frame, tb_frame.f_lasti, tb_frame.f_lineno)
    return exc.with_traceback(tb)


T = TypeVar("T", bound=Callable[..., Any])


# Decorators to wrap prediction methods to simplify tracebacks
def wrap_modelkit_exceptions(func: T) -> T:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if kwargs.pop("__internal", False):
            return func(*args, **kwargs)
        else:
            try:
                return func(*args, **kwargs)
            except PredictionError as exc:
                if os.environ.get("MODELKIT_ENABLE_SIMPLE_TRACEBACK", "True") == "True":
                    raise strip_modelkit_traceback_frames(exc.exc)
                raise exc.exc
            except BaseException:
                raise

    return cast(T, wrapper)


def wrap_modelkit_exceptions_gen(func: T) -> T:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if kwargs.pop("__internal", False):
            yield from func(*args, **kwargs)
        else:
            try:
                yield from func(*args, **kwargs)
            except PredictionError as exc:
                if os.environ.get("MODELKIT_ENABLE_SIMPLE_TRACEBACK", "True") == "True":
                    raise strip_modelkit_traceback_frames(exc.exc)
                raise exc.exc
            except BaseException:
                raise

    return cast(T, wrapper)


def wrap_modelkit_exceptions_async(func: T) -> T:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if kwargs.pop("__internal", False):
            return await func(*args, **kwargs)
        else:
            try:
                return await func(*args, **kwargs)
            except PredictionError as exc:
                if os.environ.get("MODELKIT_ENABLE_SIMPLE_TRACEBACK", "True") == "True":
                    raise strip_modelkit_traceback_frames(exc.exc)
                raise exc.exc
            except BaseException:
                raise

    return cast(T, wrapper)


def wrap_modelkit_exceptions_gen_async(func: T) -> T:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if kwargs.pop("__internal", False):
            async for x in func(*args, **kwargs):
                yield x
        else:
            try:
                async for x in func(*args, **kwargs):
                    yield x
            except PredictionError as exc:
                if os.environ.get("MODELKIT_ENABLE_SIMPLE_TRACEBACK", "True") == "True":
                    raise strip_modelkit_traceback_frames(exc.exc)
                raise exc.exc
            except BaseException:
                raise

    return cast(T, wrapper)
