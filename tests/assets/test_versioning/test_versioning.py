from modelkit.assets.versioning.versioning import AssetsVersioningSystem

INIT_VERSIONING_PARAMETRIZE = (
    "version_asset_name, version, versioning",
    [
        ("asset", "0.0", None),
        ("asset", "0.0", "major_minor"),
        ("simple_date_asset", "2021-11-14T18-00-00Z", "simple_date"),
    ],
)


TWO_VERSIONING_PARAMETRIZE = (
    "version_asset_name, version_1, version_2, versioning",
    [
        ("asset", "0.0", "1.0", None),
        ("asset", "0.0", "1.0", "major_minor"),
        (
            "simple_date_asset",
            "2021-11-14T18-00-00Z",
            "2021-11-15T17-31-06Z",
            "simple_date",
        ),
    ],
)  #  version_2 is latest version and > version_1


def test_is_version_complete():
    assert AssetsVersioningSystem.is_version_complete("any_version")


def test_get_latest_partial_version():
    assert (
        AssetsVersioningSystem.get_latest_partial_version(
            "any_version", ["any", "version", "list"]
        )
        == "any"
    )
