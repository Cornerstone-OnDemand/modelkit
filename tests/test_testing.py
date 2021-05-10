import datetime
import decimal
import json
import os
import tempfile

import pytest

from modelkit.utils.testing import ReferenceJson, ReferenceText, deep_format_floats


def test_referencejson(monkeypatch):
    monkeypatch.setenv("UPDATE_REF", "0")
    with tempfile.TemporaryDirectory(prefix="common-") as tempdir:
        with open(os.path.join(tempdir, "test.json"), "w") as f:
            print('"value"', end="", file=f)
        r = ReferenceJson(tempdir)
        r.assert_equal("test.json", "value")
        with pytest.raises(AssertionError):
            r.assert_equal("test.json", "stuff")
        with pytest.raises(AssertionError):
            r.assert_equal("fake.json", "stuff")
        r.assert_equal("test.json", "new value", update_ref=True)
        with open(os.path.join(tempdir, "test.json")) as f:
            assert f.read() == '"new value"'

        # Test directory creation
        tempdir = os.path.join(tempdir, "sub")
        r = ReferenceJson(tempdir)
        r.assert_equal("sub2/test.json", "new value", update_ref=True)
        with open(os.path.join(tempdir, "sub2/test.json")) as f:
            assert f.read() == '"new value"'

        # Test non-serializable values
        r = ReferenceJson(tempdir)
        obj = {
            "date": datetime.date(2019, 1, 1),
            "datetime": datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc),
            "decimal": decimal.Decimal("0.1"),
        }
        r.assert_equal("objects.json", obj, update_ref=True)
        with open(os.path.join(tempdir, "objects.json")) as f:
            assert json.load(f) == {
                "date": "2019-01-01",
                "datetime": "2019-01-01T00:00:00+00:00",
                "decimal": "0.1",
            }
        with pytest.raises(TypeError, match="Unexpected function"):
            r.assert_equal("objects.json", lambda f: None)


def test_referencetext(monkeypatch):
    monkeypatch.setenv("UPDATE_REF", "0")
    with tempfile.TemporaryDirectory(prefix="common-") as tempdir:
        with open(os.path.join(tempdir, "test.txt"), "w") as f:
            for i in range(3):
                print(f"value {i}", file=f)
        r = ReferenceText(tempdir)
        r.assert_equal("test.txt", ["value 0", "value 1", "value 2"])
        with pytest.raises(AssertionError):
            r.assert_equal("test.json", ["value 0"])
        with pytest.raises(AssertionError):
            r.assert_equal("fake.json", ["stuff"])
        r.assert_equal("test.json", ["value 0", "value 1"], update_ref=True)
        with open(os.path.join(tempdir, "test.json")) as f:
            assert f.read() == "value 0\nvalue 1\n"

        # Test single string input
        r.assert_equal("test.json", "value 0\nvalue 1")
        r.assert_equal("test.json", "value 0\nvalue 2", update_ref=True)
        with open(os.path.join(tempdir, "test.json")) as f:
            assert f.read() == "value 0\nvalue 2\n"


def test_deep_format_floats():
    assert deep_format_floats(1) == 1
    assert deep_format_floats("a") == "a"
    assert deep_format_floats(1.2) == "1.20000"
    assert deep_format_floats({"a": [1.2, 1, 2, 3]}) == {"a": ["1.20000", 1, 2, 3]}
    assert deep_format_floats({"a": [1.2345, 3]}, depth=2) == {"a": ["1.23", 3]}
    assert deep_format_floats({"a": 1.2345}, depth=2) == {"a": "1.23"}
    assert deep_format_floats({"a": [1.2345, {"b": 1.2345}]}, depth=2) == {
        "a": ["1.23", {"b": "1.23"}]
    }
