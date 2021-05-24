import datetime
import decimal
import difflib
import json
import os
import traceback
from collections.abc import Iterable
from typing import Any


def _diff_lines(ref_name, ref_lines, lines):
    if ref_lines == lines:
        return
    diff = list(
        difflib.unified_diff(ref_lines, lines, fromfile=ref_name, tofile="test output")
    )
    diff = "".join(diff)
    assert False, diff


def json_serializer(obj):
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, decimal.Decimal):
        return str(obj)
    raise TypeError("Unexpected " + obj.__class__.__name__)


DUMP_KWARGS = {
    "indent": 2,
    "sort_keys": True,
    "ensure_ascii": False,
    "default": json_serializer,
}


def _diff_entities(ref_name, ref_doc, doc):
    ref_js = json.dumps(ref_doc, **DUMP_KWARGS)
    js = json.dumps(doc, **DUMP_KWARGS)
    return _diff_lines(ref_name, ref_js.splitlines(True), js.splitlines(True))


class Reference:
    def __init__(self, path):
        self.path = path

    def load(self, name):
        path = os.path.join(self.path, name)
        try:
            with open(path, encoding="utf-8") as fp:
                return self._load(fp)
        except FileNotFoundError:
            return self.DEFAULT_VALUE

    def save(self, name, doc):
        path = os.path.join(self.path, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fp:
            self._save(doc, fp)

    def assert_equal(self, name, doc, update_ref=False):
        if update_ref or os.environ.get("UPDATE_REF") == "1":
            self.save(name, doc)
        ref = self.load(name)
        self._diff(name, ref, doc)


class ReferenceJson(Reference):
    DEFAULT_VALUE: Any = {}

    def _load(self, fp):
        return json.load(fp)

    def _save(self, doc, fp):
        json.dump(doc, fp, **DUMP_KWARGS)

    def _diff(self, ref_name, ref, doc):
        _diff_entities(ref_name, ref, doc)


def _ensure_lines(lines):
    if isinstance(lines, str):
        lines = lines.splitlines(False)
    return lines


class ReferenceText(Reference):
    """ReferenceText input is either a sequence of lines without LF or a single string
    to be split into lines on LF
    """

    DEFAULT_VALUE = ""

    def _load(self, fp):
        return fp.read()

    def _save(self, doc, fp):
        doc = _ensure_lines(doc)
        for line in doc:
            print(line.rstrip("\n"), file=fp)

    def _diff(self, ref_name, ref, doc):
        doc = _ensure_lines(doc)
        lines = [line + "\n" for line in doc]
        _diff_lines(ref_name, ref.splitlines(True), lines)


def click_invoke(runner, cmd_fn, args, env=None):
    res = runner.invoke(cmd_fn, args, env=env)
    if res.exception is not None and res.exc_info[0] != SystemExit:
        traceback.print_exception(*res.exc_info)
    return res


def deep_format_floats(obj, depth=5):
    # case str, is container but should be returned as is
    if type(obj) is str:
        return obj
    # deep recursive call for any container
    elif isinstance(obj, dict):
        return {k: deep_format_floats(v, depth) for k, v in obj.items()}
    elif isinstance(obj, Iterable):
        return type(obj)(deep_format_floats(v, depth) for v in obj)
    # format float
    elif isinstance(obj, float):
        return ("{:." + str(depth) + "f}").format(obj)
    # else, return as is
    else:
        return obj
