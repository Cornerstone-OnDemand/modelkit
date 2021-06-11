import functools
import inspect
import os
import traceback
import types
from typing import Any, Callable, TypeVar, cast


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
        try:
            return func(*args, **kwargs)
        except BaseException as exc:
            if os.environ.get("ENABLE_SIMPLE_TRACEBACK", "True") == "True":
                raise strip_modelkit_traceback_frames(exc)
            raise exc

    return cast(T, wrapper)


def wrap_modelkit_exceptions_gen(func: T) -> T:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            yield from func(*args, **kwargs)
        except BaseException as exc:
            if os.environ.get("ENABLE_SIMPLE_TRACEBACK", "True") == "True":
                raise strip_modelkit_traceback_frames(exc)
            raise exc

    return cast(T, wrapper)


def wrap_modelkit_exceptions_async(func: T) -> T:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except BaseException as exc:
            if os.environ.get("ENABLE_SIMPLE_TRACEBACK", "True") == "True":
                raise strip_modelkit_traceback_frames(exc)
            raise exc

    return cast(T, wrapper)


def wrap_modelkit_exceptions_gen_async(func: T) -> T:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            async for x in func(*args, **kwargs):
                yield x
        except BaseException as exc:
            if os.environ.get("ENABLE_SIMPLE_TRACEBACK", "True") == "True":
                raise strip_modelkit_traceback_frames(exc)
            raise exc

    return cast(T, wrapper)
