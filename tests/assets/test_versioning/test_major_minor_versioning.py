import os

import pytest

import tests
from modelkit.assets import errors
from modelkit.assets.settings import AssetSpec
from modelkit.assets.versioning.major_minor import (
    InvalidMajorVersionError,
    MajorMinorAssetsVersioningSystem,
    MajorVersionDoesNotExistError,
)

TEST_CASES_PARSE = [
    ("ok", False, None),
    ("1.", False, None),
    ("_", False, None),
    ("a_", False, None),
    ("a.a", False, None),
    ("1.a", False, None),
    ("a.1", False, None),
    (".1", False, None),
    ("12.", False, None),
    ("1/2", False, None),
    ("1\2", False, None),
    ("", True, None),
    (None, True, (None, None)),
    ("1", True, (1, None)),
    ("1.1", True, (1, 1)),
    ("10.1", True, (10, 1)),
    ("10.10", True, (10, 10)),
    ("123.4", True, (123, 4)),
]


@pytest.mark.parametrize("version, valid, values", TEST_CASES_PARSE)
def test_parse_version(version, valid, values):
    if version is None:
        return

    if valid and version != "":
        assert MajorMinorAssetsVersioningSystem._parse_version(version) == values
    else:
        with pytest.raises(errors.InvalidVersionError):
            MajorMinorAssetsVersioningSystem._parse_version(version)


@pytest.mark.parametrize("version, valid, values", TEST_CASES_PARSE)
def test_check_version_valid(version, valid, values):
    if valid:
        MajorMinorAssetsVersioningSystem.check_version_valid(version)
        assert MajorMinorAssetsVersioningSystem().is_version_valid(version)
    else:
        with pytest.raises(errors.InvalidVersionError):
            MajorMinorAssetsVersioningSystem.check_version_valid(version)
        assert not MajorMinorAssetsVersioningSystem().is_version_valid(version)


TEST_CASES_INCREMENT = [
    (["0.0"], False, None, True, "0.1"),
    (["0.0"], False, "0", True, "0.1"),
    (["0.0"], True, None, True, "1.0"),
    (["0.9"], False, None, True, "0.10"),
    (["0.9", "1.0"], False, None, True, "1.1"),
    (["0.9", "1.0"], False, "0", True, "0.10"),
    (["9.0"], True, None, True, "10.0"),
    (["123.456"], False, None, True, "123.457"),
    (["123.456"], True, None, True, "124.0"),
    (["123.456"], True, "0", True, "124.0"),
    (["123.456"], False, "0", False, None),
]


@pytest.mark.parametrize(
    "string, bump_major, major, valid, result", TEST_CASES_INCREMENT
)
def test_minor_major_increment_version(string, bump_major, major, valid, result):
    if valid:
        assert (
            MajorMinorAssetsVersioningSystem.increment_version(
                string, params={"bump_major": bump_major, "major": major}
            )
            == result
        )
    else:
        with pytest.raises(MajorVersionDoesNotExistError):
            MajorMinorAssetsVersioningSystem.increment_version(
                string, params={"bump_major": bump_major, "major": major}
            )


TEST_CASES_SORT = [
    (["0.0", "1.0", "2.0"], ["2.0", "1.0", "0.0"]),
    (["0.0", "2.0"], ["2.0", "0.0"]),
    (["0.0", "0.1", "0.2"], ["0.2", "0.1", "0.0"]),
    (["0.0", "0.1", "1.0", "1.1"], ["1.1", "1.0", "0.1", "0.0"]),
    (["0.2", "0.10", "2"], ["2", "0.10", "0.2"]),
]


@pytest.mark.parametrize("version_list, result", TEST_CASES_SORT)
def test_sort_versions(version_list, result):
    assert MajorMinorAssetsVersioningSystem.sort_versions(version_list) == result


TEST_CASES_FILTER = [
    (["0.0", "1.0", "2.0"], "0", True, ["0.0"]),
    (["0.0", "1.0", "2.0"], "ok", False, None),
    (
        ["123.0", "123.1", "123.2", "0.1", "1.2", "2.3", "3.4"],
        "123",
        True,
        ["123.0", "123.1", "123.2"],
    ),
]


@pytest.mark.parametrize("version_list, major, valid, result", TEST_CASES_FILTER)
def test_filter_versions(version_list, major, valid, result):
    if valid:
        assert (
            list(MajorMinorAssetsVersioningSystem.filter_versions(version_list, major))
            == result
        )
    else:
        with pytest.raises(InvalidMajorVersionError):
            MajorMinorAssetsVersioningSystem.filter_versions(version_list, major)


TEST_CASES_LATEST = [
    (["0.0", "1.0", "2.0"], None, True, "2.0"),
    (["0.0", "1.0", "2.0"], "1", True, "1.0"),
    (["0.0", "1.0", "2.0"], "123", False, None),
    (["123.0", "123.1", "123.2", "0.1", "1.2", "2.3", "3.4"], "123", True, "123.2"),
]


@pytest.mark.parametrize("version_list, major, valid, result", TEST_CASES_LATEST)
def test_latest_version(version_list, major, valid, result):
    if valid:
        assert (
            MajorMinorAssetsVersioningSystem.latest_version(version_list, major)
            == result
        )
    else:
        with pytest.raises(MajorVersionDoesNotExistError):
            MajorMinorAssetsVersioningSystem.latest_version(version_list, major)


def test_get_initial_version():
    assert MajorMinorAssetsVersioningSystem.get_initial_version() == "0.0"
    MajorMinorAssetsVersioningSystem.check_version_valid(
        MajorMinorAssetsVersioningSystem.get_initial_version()
    )


@pytest.mark.parametrize(
    "version, bump_major, major",
    [
        ("1.0", True, "1"),
        ("2.1", False, "2"),
    ],
)
def test_get_update_cli_params(version, bump_major, major):
    res = MajorMinorAssetsVersioningSystem.get_update_cli_params(
        version=version,
        version_list=["1.1", "1.0", "0.1", "0.0"],
        bump_major=bump_major,
    )
    assert res["params"] == {"bump_major": bump_major, "major": major}


TEST_SPECS = [
    ({"name": "blebla/blabli"}, True),
    ({"name": "blabli"}, True),
    ({"name": "ontologies/skills.csv", "version": "1"}, True),
    ({"name": "ontologies/skills.csv", "version": "1.1"}, True),
    ({"name": "ontologies/skills.csv", "version": "1.1.1"}, False),
    ({"name": "ontologies/skills.csv", "version": "10"}, True),
    ({"name": "ontologies/skills.csv", "version": ".10"}, False),
    ({"name": "ontologies/skills.csv:", "version": "1"}, False),
]


@pytest.mark.parametrize("spec_dict, valid", TEST_SPECS)
def test_create_asset(spec_dict, valid):
    if valid:
        AssetSpec(**spec_dict)  #  major_minor is default system
        AssetSpec(**spec_dict, versioning="major_minor")
    else:
        with pytest.raises(errors.InvalidAssetSpecError):
            AssetSpec(**spec_dict)


def test_asset_spec_is_version_complete():
    spec = AssetSpec(name="name", version="1.1", versioning="major_minor")
    assert spec.is_version_complete()

    spec = AssetSpec(name="name", version="1", versioning="major_minor")
    assert not spec.is_version_complete()

    spec = AssetSpec(name="name", versioning="major_minor")
    assert not spec.is_version_complete()


TEST_CASES_SORT = [
    (["0.0", "1.0", "2.0"], ["2.0", "1.0", "0.0"]),
    (["0.0", "2.0"], ["2.0", "0.0"]),
    (["0.0", "0.1", "0.2"], ["0.2", "0.1", "0.0"]),
    (["0.0", "0.1", "1.0", "1.1"], ["1.1", "1.0", "0.1", "0.0"]),
    (["0.2", "0.10", "2"], ["2", "0.10", "0.2"]),
]


@pytest.mark.parametrize("version_list, result", TEST_CASES_SORT)
def test_asset_spec_sort_versions(version_list, result):
    spec = AssetSpec(name="name", versioning="major_minor")
    assert spec.sort_versions(version_list) == result


def test_asset_spec_get_local_versions():
    spec = AssetSpec(name="name", versioning="major_minor")
    assert spec.get_local_versions("not_a_dir") == []
    asset_dir = ["testdata", "test-bucket", "assets-prefix", "category", "asset"]
    local_path = os.path.join(tests.TEST_DIR, *asset_dir)
    assert spec.get_local_versions(local_path) == ["1.0", "0.1", "0.0"]


@pytest.mark.parametrize(
    "test, valid",
    [("_", False), ("a_", False), ("", True), (None, True), ("1", True), ("12", True)],
)
def test_check_version_number(test, valid):
    if valid:
        MajorMinorAssetsVersioningSystem._check_version_number(test)
    else:
        with pytest.raises(errors.InvalidVersionError):
            MajorMinorAssetsVersioningSystem._check_version_number(test)


def get_string_spec(versions):
    examples = [
        ("blabli/blebla", {"name": "blabli/blebla"}),
        ("bl2_32_a.bli/bl3.debla", {"name": "bl2_32_a.bli/bl3.debla"}),
        ("blabli/BLEBLA", {"name": "blabli/BLEBLA"}),
        ("bl2_32_a.BLI/bl3.DEBLA", {"name": "bl2_32_a.BLI/bl3.DEBLA"}),
        ("blabli/blebla[foo]", {"name": "blabli/blebla", "sub_part": "foo"}),
        ("blabli/blebla[/foo/bar]", {"name": "blabli/blebla", "sub_part": "/foo/bar"}),
        ("blabli/blebla[foo]", {"name": "blabli/blebla", "sub_part": "foo"}),
        (
            r"C:\A\L0cAL\Windows\file.ext",
            {
                "name": r"C:\A\L0cAL\Windows\file.ext",
                "sub_part": None,
                "version": None,
            },
        ),
        (
            "/modelkit/tmp-local-asset/1.0/subpart/README.md",
            {
                "name": "/modelkit/tmp-local-asset/1.0/subpart/README.md",
                "sub_part": None,
                "version": None,
            },
        ),
    ]
    for version in versions:
        examples += [
            (
                f"blabli/blebla:{version}[/foo/bar]",
                {"name": "blabli/blebla", "sub_part": "/foo/bar", "version": version},
            ),
            (
                f"blabli/blebla:{version}[/foo]",
                {"name": "blabli/blebla", "sub_part": "/foo", "version": version},
            ),
            (
                f"blabli/BLEBLA:{version}[FOO]",
                {"name": "blabli/BLEBLA", "sub_part": "FOO", "version": version},
            ),
        ]
    return examples


@pytest.mark.parametrize("s, spec", get_string_spec(["1", "1.2", "12"]))
def test_string_asset_spec(s, spec):
    assert AssetSpec.from_string(s) == AssetSpec(**spec)
    assert AssetSpec.from_string(s, versioning="major_minor") == AssetSpec(
        versioning="major_minor", **spec
    )


def test_asset_spec_set_latest_version():
    spec = AssetSpec(name="a", versioning="major_minor")
    spec.set_latest_version(["3", "2.1", "1.3"])
    assert spec.version == "3"

    spec = AssetSpec(name="a", version="2", versioning="major_minor")
    spec.set_latest_version(["3", "2.1", "2.0", "1.3"])
    assert spec.version == "2.1"

    spec = AssetSpec(name="a", version="1.1", versioning="major_minor")
    spec.set_latest_version(["3", "2.1", "2.0", "1.3"])
    assert spec.version == "1.3"
