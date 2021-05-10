import contextlib
import platform

import humanize

from modelkit.log import logger

# 'resource' isn't supported on Windows
try:
    import resource
except ModuleNotFoundError:
    pass


@contextlib.contextmanager
def log_memory_increment(model_name):
    if platform.system() == "Windows":
        yield
        return

    pre_maxrss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    yield
    post_maxrss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    memory_increment = post_maxrss_bytes - pre_maxrss_bytes
    logger.debug(
        "Asset deserialized",
        model_name=model_name,
        memory=humanize.naturalsize(memory_increment),
        memory_bytes=memory_increment,
    )


def log_memory_usage():
    if platform.system() == "Windows":
        return

    maxrss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    logger.info(
        "Max memory usage after startup event",
        memory=humanize.naturalsize(maxrss_bytes),
        memory_bytes=maxrss_bytes,
    )
