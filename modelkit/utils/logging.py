from structlog import contextvars


class ContextualizedLogging:
    def __init__(self, **kwargs):
        self._context = kwargs

    def __enter__(self):
        self._existing_vars = contextvars.merge_contextvars(
            logger=None, method_name=None, event_dict={}
        )
        contextvars.bind_contextvars(**self._context)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        [contextvars.unbind_contextvars(key) for key in self._context]
        contextvars.bind_contextvars(**self._existing_vars)
