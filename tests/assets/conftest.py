import os
import subprocess
import tempfile
import uuid

import pytest

from modelkit.assets.manager import AssetsManager
from modelkit.assets.settings import DriverSettings

test_path = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(scope="function")
def base_dir():
    with tempfile.TemporaryDirectory() as base_dir:
        yield base_dir


@pytest.fixture(scope="function")
def working_dir(base_dir):
    working_dir = os.path.join(base_dir, "working_dir")
    os.makedirs(working_dir)

    yield working_dir


def _delete_all_objects(mng):
    for object_name in mng.storage_driver.iterate_objects(
        mng.bucket, mng.assetsmanager_prefix
    ):
        mng.storage_driver.delete_object(mng.bucket, object_name)


@pytest.fixture(scope="function")
def local_assetsmanager(base_dir, working_dir):
    bucket_path = os.path.join(base_dir, "local_driver", "bucket")
    os.makedirs(bucket_path)

    mng = AssetsManager(
        driver_settings={
            "storage_provider": "local",
            "bucket": bucket_path,
        },
        working_dir=working_dir,
    )
    yield mng
    _delete_all_objects(mng)


@pytest.fixture(scope="function")
def gcs_assetsmanager(working_dir):
    mng = AssetsManager(
        driver_settings=DriverSettings(
            storage_provider="gcs",
            service_account_path=None,
            bucket="modelkit-test-bucket",
        ),
        working_dir=working_dir,
        assetsmanager_prefix=f"test-assets-{uuid.uuid1().hex}",
    )
    yield mng
    _delete_all_objects(mng)


@pytest.fixture(scope="function")
def s3_assetsmanager(request, base_dir, working_dir):
    driver_path = os.path.join(base_dir, "local_driver")
    os.makedirs(driver_path)
    os.makedirs(os.path.join(driver_path, "mlp-build-assets"))

    if "GITLAB_CI" in os.environ or "MINIO_PROCESS" in os.environ:
        minio_proc = subprocess.Popen(
            ["/usr/local/bin/minio", "server", driver_path, "--address", ":9000"],
            env={"MINIO_BROWSER": "off", **os.environ},
        )

        def finalize():
            minio_proc.terminate()

    else:
        # kill previous minio container (if any)
        subprocess.call(
            ["docker", "rm", "-f", "storage-minio-tests"], stderr=subprocess.DEVNULL
        )
        # start minio as docker container
        minio_proc = subprocess.Popen(
            [
                "docker",
                "run",
                "-p",
                "9000:9000",
                "--name",
                "storage-minio-tests",
                "--volume",
                f"{driver_path}:/data",
                "minio/minio",
                "server",
                "/data",
            ]
        )

        def finalize():
            subprocess.call(["docker", "stop", "storage-minio-tests"])
            minio_proc.terminate()

    request.addfinalizer(finalize)

    mng = AssetsManager(
        driver_settings={
            "storage_provider": "s3",
            "aws_default_region": "us-east-1",
            "bucket": "mlp-build-assets",
            "aws_access_key_id": "minioadmin",
            "aws_secret_access_key": "minioadmin",
            "aws_session_token": None,
            "s3_endpoint": "http://127.0.0.1:9000",
        },
        working_dir=working_dir,
        assetsmanager_prefix=f"test-assets-{uuid.uuid1().hex}",
    )
    yield mng
    _delete_all_objects(mng)
