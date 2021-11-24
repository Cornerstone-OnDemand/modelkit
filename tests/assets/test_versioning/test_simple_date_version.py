import json
import os
import time

import pytest
from test_major_minor_versioning import get_string_spec

import modelkit
import tests
from modelkit.assets import errors
from modelkit.assets.settings import AssetSpec
from modelkit.assets.versioning.simple_date import SimpleDateAssetsVersioningSystem


@pytest.mark.parametrize(
    "version,valid",
    [
        ("2021-11-15T17-30-56Z", True),
        ("0000-00-00T00-00-00Z", True),
        ("9999-99-99T99-99-99Z", True),
        ("2021-11-15T17-30-56", False),
        ("21-11-15T17-30-56Z", False),
        ("", False),
    ],
)
def test_check_version_valid(version, valid):
    if valid:
        SimpleDateAssetsVersioningSystem.check_version_valid(version)
        assert SimpleDateAssetsVersioningSystem().is_version_valid(version)
    else:
        with pytest.raises(errors.InvalidVersionError):
            SimpleDateAssetsVersioningSystem.check_version_valid(version)
        assert not SimpleDateAssetsVersioningSystem().is_version_valid(version)


def test_get_initial_version():
    SimpleDateAssetsVersioningSystem.check_version_valid(
        SimpleDateAssetsVersioningSystem.get_initial_version()
    )


def test_sort_versions():
    assert SimpleDateAssetsVersioningSystem.sort_versions(
        [
            "2021-11-15T17-30-56Z",
            "2020-11-15T17-30-56Z",
            "2021-10-15T17-30-56Z",
        ]
    ) == [
        "2021-11-15T17-30-56Z",
        "2021-10-15T17-30-56Z",
        "2020-11-15T17-30-56Z",
    ]


def test_get_update_cli_params():
    res = SimpleDateAssetsVersioningSystem.get_update_cli_params(
        version_list=[
            "2021-11-15T17-30-56Z",
            "2021-10-15T17-30-56Z",
            "2020-11-15T17-30-56Z",
        ]
    )
    assert res["params"] == {}


def test_increment_version():

    v1 = SimpleDateAssetsVersioningSystem.get_initial_version()
    time.sleep(2)
    v2 = SimpleDateAssetsVersioningSystem.increment_version()
    time.sleep(2)
    v3 = SimpleDateAssetsVersioningSystem.increment_version()
    assert SimpleDateAssetsVersioningSystem.sort_versions([v1, v2, v3]) == [v3, v2, v1]


def test_create_asset():
    spec = AssetSpec(
        name="name", version="2020-11-15T17-30-56Z", versioning="simple_date"
    )
    assert isinstance(spec.versioning, SimpleDateAssetsVersioningSystem)

    with pytest.raises(errors.InvalidVersionError):
        AssetSpec(name="name", version="2020-11-15T17-30-56", versioning="simple_date")


def test_load_model(working_dir, monkeypatch):
    class MyModel(modelkit.Model):
        CONFIGURATIONS = {
            "my_model": {"asset": "category/simple_date_asset:2021-11-14T18-00-00Z"},
            "my_last_model": {"asset": "category/simple_date_asset"},
        }

        def _load(self):
            with open(self.asset_path) as f:
                self.data = json.load(f)

        def _predict(self, item, **kwargs):
            return self.data["name"]

    monkeypatch.setenv("MODELKIT_ASSETS_DIR", working_dir)
    monkeypatch.setenv("MODELKIT_ASSETS_VERSIONING_SYSTEM", "simple_date")
    monkeypatch.setenv("MODELKIT_STORAGE_PROVIDER", "local")
    monkeypatch.setenv(
        "MODELKIT_STORAGE_BUCKET",
        os.path.join(tests.TEST_DIR, "testdata", "test-bucket"),
    )
    monkeypatch.setenv("MODELKIT_STORAGE_PREFIX", "assets-prefix")

    model = modelkit.load_model("my_model", models=MyModel)
    assert model.predict({}) == "asset-2021-11-14T18-00-00Z"

    my_last_model = modelkit.load_model("my_last_model", models=MyModel)
    assert my_last_model.predict({}) == "asset-2021-11-15T17-31-06Z"


def test_asset_spec_sort_versions():
    spec = AssetSpec(name="name", versioning="simple_date")
    version_list = [
        "2021-11-15T17-30-56Z",
        "2020-11-15T17-30-56Z",
        "2021-10-15T17-30-56Z",
    ]
    result = [
        "2021-11-15T17-30-56Z",
        "2021-10-15T17-30-56Z",
        "2020-11-15T17-30-56Z",
    ]
    assert spec.sort_versions(version_list) == result


def test_asset_spec_get_local_versions():
    spec = AssetSpec(name="name", versioning="simple_date")
    assert spec.get_local_versions("not_a_dir") == []
    asset_dir = [
        "testdata",
        "test-bucket",
        "assets-prefix",
        "category",
        "simple_date_asset",
    ]
    local_path = os.path.join(tests.TEST_DIR, *asset_dir)
    assert spec.get_local_versions(local_path) == [
        "2021-11-15T17-31-06Z",
        "2021-11-14T18-00-00Z",
    ]


@pytest.mark.parametrize("s, spec", get_string_spec(["2021-11-14T18-00-00Z"]))
def test_string_asset_spec(s, spec):
    assert AssetSpec.from_string(s, versioning="simple_date") == AssetSpec(
        versioning="simple_date", **spec
    )


def test_asset_spec_set_latest_version():
    spec = AssetSpec(name="a", versioning="simple_date")
    spec.set_latest_version(["2021-11-15T17-31-06Z", "2021-11-14T18-00-00Z"])
    assert spec.version == "2021-11-15T17-31-06Z"

    spec = AssetSpec(name="a", version="2021-11-14T18-00-00Z", versioning="simple_date")
    spec.set_latest_version(["2021-11-15T17-31-06Z", "2021-11-14T18-00-00Z"])
    assert spec.version == "2021-11-15T17-31-06Z"
