import os
import shutil
import subprocess
import tempfile
import uuid

import pytest
import requests
import urllib3
from google.api_core.client_options import ClientOptions
from google.auth.credentials import AnonymousCredentials
from google.cloud import storage
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

from modelkit.assets.manager import AssetsManager
from modelkit.assets.remote import RemoteAssetsStore

test_path = os.path.dirname(os.path.realpath(__file__))


def _delete_all_objects(mng):
    for object_name in mng.remote_assets_store.storage_driver.iterate_objects(
        mng.remote_assets_store.bucket, mng.remote_assets_store.prefix
    ):
        mng.remote_assets_store.storage_driver.delete_object(
            mng.remote_assets_store.bucket, object_name
        )


@pytest.fixture(scope="function")
def local_assetsmanager(base_dir, working_dir, clean_env):
    bucket_path = os.path.join(base_dir, "local_driver", "bucket")
    os.makedirs(bucket_path)

    mng = AssetsManager(
        assets_dir=working_dir,
        remote_store={
            "storage_driver": {
                "storage_provider": "local",
                "bucket": bucket_path,
            }
        },
    )
    yield mng
    _delete_all_objects(mng)


def _get_mock_gcs_client():
    my_http = requests.Session()
    my_http.verify = False  # disable SSL validation
    urllib3.disable_warnings(
        urllib3.exceptions.InsecureRequestWarning
    )  # disable https warnings for https insecure certs

    return storage.Client(
        credentials=AnonymousCredentials(),
        project="test",
        _http=my_http,
        client_options=ClientOptions(api_endpoint="https://127.0.0.1:4443"),
    )


@pytest.fixture(scope="function")
def gcs_assetsmanager(request, working_dir, clean_env):
    # kill previous fake gcs container (if any)
    subprocess.call(
        ["docker", "rm", "-f", "storage-gcs-tests"], stderr=subprocess.DEVNULL
    )
    # start minio as docker container
    minio_proc = subprocess.Popen(
        [
            "docker",
            "run",
            "-p",
            "4443:4443",
            "--name",
            "storage-gcs-tests",
            "fsouza/fake-gcs-server",
        ]
    )

    def finalize():
        subprocess.call(["docker", "stop", "storage-gcs-tests"])
        minio_proc.terminate()
        minio_proc.wait()

    request.addfinalizer(finalize)

    mng = AssetsManager(
        assets_dir=working_dir,
    )
    remote_store = RemoteAssetsStore(
        assetsmanager_prefix="test-prefix",
        storage_driver={
            "storage_provider": "gcs",
            "settings": {"bucket": "test-bucket", "client": _get_mock_gcs_client()},
        },
    )
    remote_store.storage_driver.client.create_bucket("test-bucket")
    mng.remote_assets_store = remote_store

    yield mng


@retry(
    wait=wait_random_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception(lambda x: isinstance(x, Exception)),
    reraise=True,
)
def _start_s3_manager(working_dir):
    return AssetsManager(
        assets_dir=working_dir,
        remote_store={
            "storage_driver": {
                "storage_provider": "s3",
                "aws_default_region": "us-east-1",
                "bucket": "test-assets",
                "aws_access_key_id": "minioadmin",
                "aws_secret_access_key": "minioadmin",
                "aws_session_token": None,
                "s3_endpoint": "http://127.0.0.1:9000",
            },
            "assetsmanager_prefix": f"test-assets-{uuid.uuid1().hex}",
        },
    )


@pytest.fixture(scope="function")
def s3_assetsmanager(request, clean_env):
    base_dir = tempfile.mkdtemp()
    driver_path = os.path.join(base_dir, "local_driver")
    working_dir = os.path.join(base_dir, "working_dir")
    os.makedirs(driver_path)
    os.makedirs(working_dir)
    os.makedirs(os.path.join(driver_path, "test-assets"))

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
        minio_proc.wait()
        shutil.rmtree(base_dir)

    request.addfinalizer(finalize)

    return _start_s3_manager(working_dir)
