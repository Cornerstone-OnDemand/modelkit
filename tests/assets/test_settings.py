import os

import pytest
from google.auth.exceptions import DefaultCredentialsError

from modelkit.assets.manager import AssetsManager
from modelkit.assets.remote import UnknownDriverError

test_path = os.path.dirname(os.path.realpath(__file__))


@pytest.mark.parametrize(
    "settings_dict, env_vars, valid, exception, has_storage_provider",
    [
        (
            {},
            {},
            True,
            None,
            False,
        ),
        (
            {
                "assets_dir": test_path,
            },
            {},
            True,
            None,
            False,
        ),
        (
            {"assets_dir": test_path, "timeout": 20},
            {},
            True,
            None,
            False,
        ),
        (
            {},
            {
                "MODELKIT_ASSETS_DIR": test_path,
                "MODELKIT_ASSETS_TIMEOUT_S": "100",
            },
            True,
            None,
            False,
        ),
        (
            {"timeout": 20},
            {
                "MODELKIT_ASSETS_DIR": test_path,
            },
            True,
            None,
            False,
        ),
        (  # fails because 20 is not a directory
            {"assets_dir": 20},
            {},
            False,
            (FileNotFoundError, TypeError),
            False,
        ),
        (  # fails because "abc" is not an int
            {"assets_dir": test_path, "timeout": "abc"},
            {},
            False,
            ValueError,
            False,
        ),
        (  # fails because "/some/path" is not a directory
            {
                "assets_dir": "/some/path",
            },
            {},
            False,
            FileNotFoundError,
            False,
        ),
        (  # fails because bucket is missing
            {
                "assets_dir": test_path,
            },
            {"MODELKIT_STORAGE_PROVIDER": "s3"},
            False,
            ValueError,
            False,
        ),
        (  # fails because bucket is missing
            {
                "assets_dir": test_path,
            },
            {"MODELKIT_STORAGE_PROVIDER": "gcs"},
            False,
            ValueError,
            False,
        ),
        (  # fails becaue GCS project is not setup
            {
                "assets_dir": test_path,
            },
            {
                "MODELKIT_STORAGE_PROVIDER": "gcs",
                "MODELKIT_STORAGE_BUCKET": "some_bucket",
            },
            False,
            (OSError, DefaultCredentialsError),
            False,
        ),
        (  # fails because bucket is missing
            {
                "assets_dir": test_path,
            },
            {"MODELKIT_STORAGE_PROVIDER": "local"},
            False,
            ValueError,
            False,
        ),
        (  # fails because bucket does not exist
            {
                "assets_dir": test_path,
            },
            {
                "MODELKIT_STORAGE_PROVIDER": "local",
                "MODELKIT_STORAGE_BUCKET": "/some/path",
            },
            False,
            FileNotFoundError,
            False,
        ),
        (  # fails because provider is not recognized
            {
                "assets_dir": test_path,
            },
            {
                "MODELKIT_STORAGE_PROVIDER": "blabla",
            },
            False,
            UnknownDriverError,
            False,
        ),
        (
            {
                "assets_dir": test_path,
            },
            {
                "MODELKIT_STORAGE_PROVIDER": "local",
                "MODELKIT_STORAGE_BUCKET": test_path,
            },
            True,
            None,
            True,
        ),
    ],
)
def test_assetsmanager_init(
    monkeypatch, settings_dict, env_vars, valid, exception, has_storage_provider
):
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    if valid:
        mng = AssetsManager(**settings_dict)
        if has_storage_provider:
            assert mng.storage_provider
    else:
        with pytest.raises(exception):
            AssetsManager(**settings_dict)


def test_assetsmanager_default_assets_dir():
    manager = AssetsManager()
    assert manager.assets_dir == os.getcwd()
    assert manager.storage_provider is None
