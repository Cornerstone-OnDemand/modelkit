import inspect
import os
import traceback
import types

_MODEL_FN = os.path.join("modelkit", "core", "model.py")
_TB_FN = os.path.join("modelkit", "utils", "traceback.py")


def is_modelkit_internal_frame(frame: types.FrameType):
    frame_info = inspect.getframeinfo(frame)
    return frame_info.filename.endswith(_MODEL_FN) or frame_info.filename.endswith(
        _TB_FN
    )


def strip_modelkit_traceback_frames(exc: BaseException):
    tb = None
    for tb_frame, _ in reversed(list(traceback.walk_tb(exc.__traceback__))):
        if not is_modelkit_internal_frame(tb_frame):
            tb = types.TracebackType(tb, tb_frame, tb_frame.f_lasti, tb_frame.f_lineno)
    return exc.with_traceback(tb)


def wrap_modelkit_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BaseException as exc:
            if os.environ.get("ENABLE_SIMPLE_TRACEBACK", "True") == "True":
                raise strip_modelkit_traceback_frames(exc)
            raise exc

    return wrapper


def wrap_modelkit_exceptions_gen(func):
    def wrapper(*args, **kwargs):
        try:
            yield from func(*args, **kwargs)
        except BaseException as exc:
            if os.environ.get("ENABLE_SIMPLE_TRACEBACK", "True") == "True":
                raise strip_modelkit_traceback_frames(exc)
            raise exc

    return wrapper
