import pytest
from pydantic import ValidationError

from modelkit.assets.settings import AssetSpec


@pytest.mark.parametrize(
    "test, valid",
    [
        ("_", False),
        ("a_", False),
        ("", False),
        (None, False),
        ("o", True),
        ("1", True),
        ("some_go0d_name", True),
        ("some_go/0d_name", True),
    ],
)
def test_names(test, valid):
    if valid:
        assert test == AssetSpec.is_name_valid(test)
    else:
        with pytest.raises(ValueError):
            AssetSpec.is_name_valid(test)


@pytest.mark.parametrize(
    "test, valid",
    [("_", False), ("a_", False), ("", True), (None, True), ("1", True), ("12", True)],
)
def test_versions(test, valid):
    if valid:
        assert test == AssetSpec.is_version_valid(test)
    else:
        with pytest.raises(ValueError):
            AssetSpec.is_version_valid(test)


TEST_SPECS = [
    ({"name": "blebla/blabli"}, True),
    ({"name": "blabli"}, True),
    ({"name": "ontologies/skills.csv", "major_version": "1"}, True),
    (
        {
            "name": "ontologies/skills.csv",
            "major_version": "1",
            "minor_version": "10",
        },
        True,
    ),
    ({"name": "ontologies/skills.csv", "minor_version": "10"}, False),
    ({"name": "ontologies/skills.csv", "major_version": "10"}, True),
    ({"name": "skills.csv", "not_a_field": "0.1", "file_path": "/ok/boomer"}, False),
]


@pytest.mark.parametrize("spec_dict, valid", TEST_SPECS)
def test_valid_spec(spec_dict, valid):
    if valid:
        assert AssetSpec(**spec_dict)
    else:
        with pytest.raises(ValidationError):
            AssetSpec(**spec_dict)


TEST_STRING_SPECS = [
    ("blabli/blebla", {"name": "blabli/blebla"}),
    ("bl2_32_a.bli/bl3.debla", {"name": "bl2_32_a.bli/bl3.debla"}),
    (
        "blabli/blebla[/foo/bar]",
        {"name": "blabli/blebla", "sub_part": "/foo/bar"},
    ),
    (
        "blabli/blebla:1.2[/foo/bar]",
        {
            "name": "blabli/blebla",
            "sub_part": "/foo/bar",
            "major_version": 1,
            "minor_version": 2,
        },
    ),
    (
        "blabli/blebla:1.12[/foo/bar]",
        {
            "name": "blabli/blebla",
            "sub_part": "/foo/bar",
            "major_version": 1,
            "minor_version": 12,
        },
    ),
    (
        "blabli/blebla:1.12[/foo/bar]",
        {
            "name": "blabli/blebla",
            "sub_part": "/foo/bar",
            "major_version": 1,
            "minor_version": 12,
        },
    ),
    (
        "blabli/blebla:12[/foo/bar]",
        {
            "name": "blabli/blebla",
            "sub_part": "/foo/bar",
            "major_version": 12,
        },
    ),
    (
        "blabli/blebla:12.1[/foo]",
        {
            "name": "blabli/blebla",
            "sub_part": "/foo",
            "major_version": 12,
            "minor_version": 1,
        },
    ),
    (
        "blabli/blebla:1.12[foo]",
        {
            "name": "blabli/blebla",
            "sub_part": "foo",
            "major_version": 1,
            "minor_version": 12,
        },
    ),
    ("blabli/blebla[foo]", {"name": "blabli/blebla", "sub_part": "foo"}),
]


@pytest.mark.parametrize("s, spec", TEST_STRING_SPECS)
def test_string_asset_spec(s, spec):
    assert AssetSpec.from_string(s) == AssetSpec(**spec)
