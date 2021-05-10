import pytest

from modelkit.assets.versioning import (
    InvalidMajorVersionError,
    InvalidVersionError,
    MajorVersionDoesNotExistError,
    filter_versions,
    increment_version,
    latest_version,
    parse_version,
    sort_versions,
)

TEST_CASES_PARSE = [
    ("ok", False, None),
    ("1.", False, None),
    ("1", True, (1, None)),
    ("1.1", True, (1, 1)),
    ("10.1", True, (10, 1)),
    ("10.10", True, (10, 10)),
    ("123.4", True, (123, 4)),
]


@pytest.mark.parametrize("string, valid, values", TEST_CASES_PARSE)
def test_parse_version(string, valid, values):
    if valid:
        assert parse_version(string) == values
    else:
        with pytest.raises(InvalidVersionError):
            parse_version(string)


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
def test_increment_version(string, bump_major, major, valid, result):
    if valid:
        assert increment_version(string, bump_major=bump_major, major=major) == result
    else:
        with pytest.raises(MajorVersionDoesNotExistError):
            increment_version(string, bump_major=bump_major, major=major)


TEST_CASES_SORT = [
    (["0.0", "1.0", "2.0"], ["2.0", "1.0", "0.0"]),
    (["0.0", "2.0"], ["2.0", "0.0"]),
    (["0.0", "0.1", "0.2"], ["0.2", "0.1", "0.0"]),
    (["0.0", "0.1", "1.0", "1.1"], ["1.1", "1.0", "0.1", "0.0"]),
    (["0.2", "0.10", "2"], ["2", "0.10", "0.2"]),
]


@pytest.mark.parametrize("versions_list, result", TEST_CASES_SORT)
def test_sort_versions(versions_list, result):
    assert sort_versions(versions_list) == result


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


@pytest.mark.parametrize("versions_list, major, valid, result", TEST_CASES_FILTER)
def test_filter_versions(versions_list, major, valid, result):
    if valid:
        assert list(filter_versions(versions_list, major)) == result
    else:
        with pytest.raises(InvalidMajorVersionError):
            filter_versions(versions_list, major)


TEST_CASES_LATEST = [
    (["0.0", "1.0", "2.0"], None, True, "2.0"),
    (["0.0", "1.0", "2.0"], "1", True, "1.0"),
    (["0.0", "1.0", "2.0"], "123", False, None),
    (["123.0", "123.1", "123.2", "0.1", "1.2", "2.3", "3.4"], "123", True, "123.2"),
]


@pytest.mark.parametrize("versions_list, major, valid, result", TEST_CASES_LATEST)
def test_latest_version(versions_list, major, valid, result):
    if valid:
        assert latest_version(versions_list, major) == result
    else:
        with pytest.raises(MajorVersionDoesNotExistError):
            latest_version(versions_list, major)
