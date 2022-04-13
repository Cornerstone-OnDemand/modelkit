import math
import platform
import time
from typing import Any, Dict

import pytest

from modelkit.core import ModelLibrary
from modelkit.core.model import Model
from modelkit.core.profilers.simple import SimpleProfiler


class ModelA(Model):
    CONFIGURATIONS: Dict[str, Any] = {"model_a": {}}

    def _predict(self, item):
        time.sleep(1)
        return item


class ModelB(Model):
    CONFIGURATIONS: Dict[str, Any] = {
        "model_b": {
            "model_dependencies": {
                "model_a",
            }
        }
    }

    def _load(self):
        self.model_a = self.model_dependencies["model_a"]

    def _predict(self, item):
        item = self.model_a.predict(item)

        time.sleep(0.5)
        return item


class ModelC(Model):
    CONFIGURATIONS: Dict[str, Any] = {"model_c": {}}

    def _predict(self, item):
        time.sleep(0.7)
        return item


class ModelD(Model):
    CONFIGURATIONS: Dict[str, Any] = {
        "model_d": {
            "model_dependencies": {
                "model_a",
            }
        }
    }

    def _load(self):
        self.model_a = self.model_dependencies["model_a"]

    def _predict(self, item):
        item = self.model_a.predict(item)

        time.sleep(0.1)
        return item


class Pipeline(Model):
    CONFIGURATIONS: Dict[str, Any] = {
        "pipeline": {
            "model_dependencies": {
                "model_b",
                "model_c",
                "model_d",
            }
        }
    }

    def _load(self):
        self.model_b = self.model_dependencies["model_b"]
        self.model_c = self.model_dependencies["model_c"]
        self.model_d = self.model_dependencies["model_d"]

    def _predict(self, item):
        item = self.model_b.predict(item)
        item = self.model_c.predict(item)
        item = self.model_d.predict(item)
        time.sleep(0.2)
        return item


def test_simple_profiler():
    model_library = ModelLibrary(models=[ModelA, ModelB, ModelC, ModelD, Pipeline])
    pipeline = model_library.get("pipeline")
    item = {"abc": 123}
    profiler = SimpleProfiler(pipeline)
    _ = pipeline.predict(item)
    stat = profiler.summary()
    assert set(stat["Name"]) == set(
        ["pipeline", "model_b", "model_a", "model_c", "model_d"]
    )

    rel_tol = 0.3
    if platform.system() == "Darwin":
        # Issue: perf_counter result does not count system sleep time in Mac OS
        # - https://bugs.python.org/issue41303
        rel_tol = 0.7

    # test total durations per model
    total_durations = dict(zip(stat["Name"], stat["Total duration (s)"]))
    assert math.isclose(total_durations["model_a"], 2.0, rel_tol=rel_tol)
    assert math.isclose(total_durations["model_b"], 1.5, rel_tol=rel_tol)
    assert math.isclose(total_durations["model_c"], 0.7, rel_tol=rel_tol)
    assert math.isclose(total_durations["model_d"], 1.1, rel_tol=rel_tol)
    assert math.isclose(total_durations["pipeline"], 3.5, rel_tol=rel_tol)

    # test duration per model
    model_durations = dict(zip(stat["Name"], stat["Duration per call (s)"]))
    assert math.isclose(model_durations["model_a"], 1.0, rel_tol=rel_tol)
    assert math.isclose(model_durations["model_b"], 1.5, rel_tol=rel_tol)
    assert math.isclose(model_durations["model_c"], 0.7, rel_tol=rel_tol)
    assert math.isclose(model_durations["model_d"], 1.1, rel_tol=rel_tol)
    assert math.isclose(model_durations["pipeline"], 3.5, rel_tol=rel_tol)

    # test net durations per call
    net_durations = dict(zip(stat["Name"], stat["Net duration per call (s)"]))
    assert math.isclose(net_durations["model_a"], 1.0, rel_tol=rel_tol)
    assert math.isclose(net_durations["model_b"], 0.5, rel_tol=rel_tol)
    assert math.isclose(net_durations["model_c"], 0.7, rel_tol=rel_tol)
    assert math.isclose(net_durations["model_d"], 0.1, rel_tol=rel_tol)
    assert math.isclose(net_durations["pipeline"], 0.2, rel_tol=rel_tol)

    # test number of call
    num_call = dict(zip(stat["Name"], stat["Num call"]))
    assert num_call == {
        "pipeline": 1,
        "model_a": 2,
        "model_b": 1,
        "model_d": 1,
        "model_c": 1,
    }

    # test net percentage ()
    assert math.isclose(sum(stat["Net percentage %"]), 100, abs_tol=1.0)

    # test total percentage ~= 100% (decreasing)
    assert math.isclose(stat["Total percentage %"][0], 99.9, abs_tol=1.0)

    # test print table
    table_str = profiler.summary(print_table=True)
    assert isinstance(table_str, str)

    # (improve test coverage)
    with pytest.raises(ValueError):
        # raise error if start the same 'action' twice without 'end'
        profiler.start("debug_start")
        profiler.start("debug_start")

    with pytest.raises(ValueError):
        # raise error if 'end' an 'action' without 'start'
        profiler.end("debug_end")
