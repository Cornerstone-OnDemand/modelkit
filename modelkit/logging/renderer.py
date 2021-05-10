from io import StringIO

import structlog
from structlog.dev import _init_colorama, _pad


class CustomConsoleRenderer(structlog.dev.ConsoleRenderer):
    """
    This is almost exactly the implementation of __call__ from
    structlog.dev.ConsoleRenderer except I include a return line
    and a tab before outputting the event_dict values.
    """

    def __call__(self, _, __, event_dict):
        # Initialize lazily to prevent import side-effects.
        if self._init_colorama:
            _init_colorama(self._force_colors)
            self._init_colorama = False
        sio = StringIO()

        ts = event_dict.pop("timestamp", None)
        if ts is not None:
            sio.write(
                # can be a number if timestamp is UNIXy
                self._styles.timestamp
                + str(ts)
                + self._styles.reset
                + " "
            )
        level = event_dict.pop("level", None)
        if level is not None:
            sio.write(
                "["
                + self._level_to_color[level]
                + _pad(level, self._longest_level)
                + self._styles.reset
                + "] "
            )

        # edit: logger name right after level
        logger_name = event_dict.pop("logger", None)
        if logger_name is not None:
            sio.write(
                "["
                + self._styles.logger_name
                + self._styles.bright
                + logger_name
                + self._styles.reset
                + "] "
            )

        # force event to str for compatibility with standard library
        event = event_dict.pop("event")
        if not isinstance(event, str):  # edit: remove PY2 check
            event = str(event)

        if event_dict:
            # edit: remove padding and trailing whitespace
            event = event + self._styles.reset
        else:
            event += self._styles.reset
        sio.write(self._styles.bright + event)

        stack = event_dict.pop("stack", None)
        exc = event_dict.pop("exception", None)
        if event_dict:
            sio.write(
                "\n\t"  # edit: Here, add a newline and padding
                + " ".join(
                    self._styles.kv_key
                    + key
                    + self._styles.reset
                    + "="
                    + self._styles.kv_value
                    + self._repr(event_dict[key])
                    + self._styles.reset
                    for key in sorted(event_dict.keys())
                )
            )

        if stack is not None:
            sio.write("\n" + stack)
            if exc is not None:
                sio.write("\n\n" + "=" * 79 + "\n")
        if exc is not None:
            sio.write("\n" + exc)

        return sio.getvalue()
