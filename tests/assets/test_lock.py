import os
import subprocess
import sys
import threading
import traceback

from modelkit.assets.remote import StorageProvider
from tests import TEST_DIR


def _start_wait_process(lock_path, duration_s):
    script_path = os.path.join(TEST_DIR, "assets", "resources", "lock.py")
    result = None

    def run():
        nonlocal result
        try:
            cmd = [sys.executable, script_path, lock_path, str(duration_s)]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            stdout, _ = p.communicate()
            stdout = stdout.decode("utf-8")
            if p.returncode:
                print("ERROR", p.returncode, stdout, flush=True)
                raise Exception("lock.py failed")
            result = stdout
        except Exception:
            traceback.print_exc()

    t = threading.Thread(target=run)
    t.daemon = True
    t.start()

    def join():
        t.join()
        return result

    return join


def test_lock_file(working_dir):
    # Start a bunch of process competing for lock
    lock_path = os.path.join(working_dir, "lock")
    threads = []
    for _ in range(3):
        t = _start_wait_process(lock_path, 2)
        threads.append(t)

    # For each process, collect the timestamp when it acquired and released
    # the lock, as well at the number of wait loops.
    ranges = []
    while threads:
        t = threads.pop()
        res = t()
        assert res is not None
        lines = res.splitlines()
        assert len(lines) == 2
        start = lines[0]
        end = lines[1]
        ranges.append((float(start), float(end)))
    ranges.sort()

    # Check the range are exclusive: the lock works assuming it got hit
    for i in range(len(ranges) - 1):
        end = ranges[i][1]
        start = ranges[i + 1][0]
        assert end <= start


def test_lock_assetsmanager(capsys, working_dir):
    assets_dir = os.path.join(working_dir, "assets_dir")
    os.makedirs(assets_dir)

    driver_path = os.path.join(working_dir, "local_driver")
    os.makedirs(os.path.join(driver_path, "bucket"))

    # push an asset
    mng = StorageProvider(
        provider="local",
        bucket=driver_path,
        prefix="prefix",
    )
    data_path = os.path.join(TEST_DIR, "assets", "testdata", "some_data_folder")
    mng.new(data_path, "category-test/some-data.ext", "0.0")

    # start 4 processes that will attempt to download it
    script_path = os.path.join(TEST_DIR, "assets", "resources", "download_asset.py")
    cmd = [
        sys.executable,
        script_path,
        assets_dir,
        driver_path,
        "category-test/some-data.ext:0.0",
    ]

    def run():
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stdout, _ = p.communicate()
        stdout = stdout.decode("utf-8")
        print(stdout)

    threads = []
    for _ in range(2):
        t = threading.Thread(target=run)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    captured = capsys.readouterr()
    assert "__ok_from_cache__" in captured.out
    assert "__ok_not_from_cache__" in captured.out
