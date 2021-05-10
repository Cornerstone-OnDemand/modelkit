#!/usr/bin/env python3
import time

import click
import filelock


@click.command()
@click.argument("lock_path")
@click.argument("duration_s", type=float)
def wait(lock_path, duration_s):
    """Take a lock, wait a bit, release the lock

    And print the acquisition and release time, as well as wait loops.
    """
    with filelock.FileLock(lock_path, 3 * 60):
        # We can't use time.monotonic() as we're comparing time between processes and
        # time.monotonic() explicitly does not support that
        # This means the test can fail during leap seconds, but this is only a test, we
        # don't need total reliability
        print(time.time())
        time.sleep(duration_s)
        print(time.time())


if __name__ == "__main__":
    wait()
