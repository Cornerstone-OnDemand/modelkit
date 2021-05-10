We use [structlog](http://www.structlog.org/en/stable/) to handle structured logs and format them either to JSON or to the console with colorized output.

### Configuration

| Environment variable | Notes                    |
| -------------------- | ------------------------ |
| `DEV_LOGGING`        | Defaults to logging JSON |
| `LOG_LEVEL`          | Defaults to `INFO`       |

### Choose logging behavior

The default behavior is to capture all logs and format them in JSON format to `stdout`.

In order to get nicely formatted logging output, set the environment variable `DEV_LOGGING` to some non falsy value.

It is therefore probably best to add `DEV_LOGGING=1` in your `.zshrc` file.

!!! info
    You will need `colorama` to be installed in your venv in order to get colorized logs.

### Using `modelkit.logging` in libraries

The best way to log in your library `cool_library` is to add a `cool_library/log.py` file
with this content:

```python
import modelkit.common.logging

logger = modelkit.common.logging.get_logger("cool_library")
```

The first line runs the basic logging configuration present in `modelkit/common/logging/__init__.py`. This is where the default logging behavior is set using a [logging.config.dictConfig](https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig), and where logs from third party libraries are captured to be formatted by `structlog`.

The `get_logger` is the one provided by the package `structlog`.

Note that although the formatting is done by `structlog`, ultimately they come out of the
standard library's `logging` module.

The rest of the file simply defines a logger, which you can then use anywhere by doing:

```python
from cool_library.log import logger

logger.info("Look at me", i_am="loggin", like_a="boss")
```

That's it, you are good to go!

## Logging format

Log messages are formatted to JSON by `structlog`, and as a result the above logging action
will result in this line being printed out:

```
{"i_am": "loggin", "like_a": "boss", "event": "Look at me", "logger": "cool_library", "level": "info", "timestamp": "2020-04-23T20:37:23.379525Z"}
```

The common contents of all log entries are:

- `timestamp` a UTC timestamp
- `level` the level of the log message
- `event` the message

Any other keyword arguments are serialized and appended to the JSON record.

## Contextualized logging

It is possible to contextually add fields to the logging using a manager present
in `cutils.logging.context`.

Assuming you are getting a `structlog` logger named `logger` somewhere (as above), use:

```python
from modelkit.common.logging.context import ContextualizedLogging

with ContextualizedLogging(some="field", for="all", other="events"):
    ...
    logger.info("Some message")
    ...

```

All events within the contextmanager will have `{"some":"field", "for":"all", "other":"events"}` appended to them.

## Further information

Refer to the official documentations for further information:

- [structlog](http://www.structlog.org/en/stable/)
- [logging](https://docs.python.org/3/library/logging.html)
