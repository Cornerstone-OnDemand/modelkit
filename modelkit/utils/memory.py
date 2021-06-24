import platform
import time

# 'resource' isn't supported on Windows
try:
    import resource
except ModuleNotFoundError:  # pragma: no cover
    # the `Windows` case is tested, but not that
    # from which coverage is gathered which runs on ubuntu
    pass


class PerformanceTracker:
    def __init__(self) -> None:
        self.increment = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        # the `Windows` case is tested, but not that
        # from which coverage is gathered which runs on ubuntu
        if platform.system() == "Windows":  # pragma: no cover
            return self
        self.pre_maxrss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return self

    def __exit__(self, *args):
        self.time = time.perf_counter() - self.start_time
        # the `Windows` case is tested, but not that
        # from which coverage is gathered which runs on ubuntu
        if platform.system() == "Windows":  # pragma: no cover
            return
        post_maxrss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        self.increment = post_maxrss_bytes - self.pre_maxrss_bytes
