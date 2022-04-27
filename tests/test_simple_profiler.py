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

    def _predict(self, item, long=None):
        if long:
            time.sleep(2)
        else:
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


class Pipeline2(Model):
    CONFIGURATIONS: Dict[str, Any] = {
        "pipeline2": {
            "model_dependencies": {
                "model_a",
                "model_b",
                "model_c",
                "model_d",
            }
        }
    }

    def _load(self):
        self.model_a = self.model_dependencies["model_a"]
        self.model_b = self.model_dependencies["model_b"]
        self.model_c = self.model_dependencies["model_c"]
        self.model_d = self.model_dependencies["model_d"]

    def _predict(self, item):
        self.model_a.predict(item, long=True)
        item = self.model_b.predict(item)
        item = self.model_c.predict(item)
        item = self.model_d.predict(item)
        time.sleep(0.2)
        return item


def test_method__get_current_sub_calls():
    model_library = ModelLibrary(models=[ModelA, ModelB, ModelC, ModelD, Pipeline])
    pipeline = model_library.get("pipeline")
    item = {"abc": 123}
    profiler = SimpleProfiler(pipeline)
    _ = pipeline.predict(item)
    assert profiler._get_current_sub_calls("pipeline") == {
        "model_a": 2,
        "model_b": 1,
        "model_d": 1,
        "model_c": 1,
    }
    assert profiler._get_current_sub_calls("model_a") == {}
    assert profiler._get_current_sub_calls("model_b") == {"model_a": 2}
    assert profiler._get_current_sub_calls("model_c") == {}
    assert profiler._get_current_sub_calls("model_d") == {"model_a": 2}


def test_method__get_all_subs():
    model_library = ModelLibrary(models=[ModelA, ModelB, ModelC, ModelD, Pipeline])
    pipeline = model_library.get("pipeline")
    item = {"abc": 123}
    profiler = SimpleProfiler(pipeline)
    _ = pipeline.predict(item)
    assert profiler._get_all_subs("pipeline") == {
        "model_a",
        "model_b",
        "model_d",
        "model_c",
    }
    assert profiler._get_all_subs("model_a") == set()
    assert profiler._get_all_subs("model_b") == {"model_a"}
    assert profiler._get_all_subs("model_c") == set()
    assert profiler._get_all_subs("model_d") == {"model_a"}


def test_method__compute_sub_calls_and_update_graph_calls():
    model_library = ModelLibrary(models=[ModelA, ModelB, ModelC, ModelD, Pipeline])
    pipeline = model_library.get("pipeline")
    item = {"abc": 123}
    profiler = SimpleProfiler(pipeline)
    _ = pipeline.predict(item)
    assert profiler._compute_sub_calls_and_update_graph_calls("pipeline", {}) == {
        "model_a": 2,
        "model_c": 1,
        "model_b": 1,
        "model_d": 1,
    }
    assert (
        profiler.graph_calls["pipeline"]["__main__"] == 2
    )  # _compute_sub_calls_and_update_graph_calls increnment "__main__"

    assert profiler._compute_sub_calls_and_update_graph_calls("model_a", {}) == {}
    assert (
        profiler.graph_calls["model_a"]["__main__"] == 3
    )  # _compute_sub_calls_and_update_graph_calls increnment "__main__"

    assert profiler._compute_sub_calls_and_update_graph_calls(
        "model_b", {"model_a": 2}
    ) == {"model_a": 1}
    assert (
        profiler.graph_calls["model_b"]["__main__"] == 2
    )  # _compute_sub_calls_and_update_graph_calls increnment "__main__"

    assert profiler._compute_sub_calls_and_update_graph_calls("model_c", {}) == {}
    assert (
        profiler.graph_calls["model_c"]["__main__"] == 2
    )  # _compute_sub_calls_and_update_graph_calls increnment "__main__"

    assert profiler._compute_sub_calls_and_update_graph_calls(
        "model_d", {"model_a": 2}
    ) == {"model_a": 1}
    assert (
        profiler.graph_calls["model_d"]["__main__"] == 2
    )  # _compute_sub_calls_and_update_graph_calls increnment "__main__"


def test_method__calculate_net_cost():
    model_library = ModelLibrary(models=[ModelA, ModelB, ModelC, ModelD, Pipeline])
    pipeline = model_library.get("pipeline")
    item = {"abc": 123}
    profiler = SimpleProfiler(pipeline)
    _ = pipeline.predict(item)
    # set artificial net_durations for test purpose only
    profiler.net_durations = {
        "model_a": [1.0, 1.01],
        "model_b": [0.5],
        "model_c": [0.7],
        "model_d": [0.1],
        "pipeline": [0.2],
    }

    # model_b
    assert math.isclose(
        profiler._calculate_net_cost(1.51, {"model_a": 1}), 0.5, abs_tol=1e-5
    )
    # model_d
    assert math.isclose(
        profiler._calculate_net_cost(1.11, {"model_a": 1}), 0.1, abs_tol=1e-5
    )
    # pipeline
    assert math.isclose(
        profiler._calculate_net_cost(
            3.51, {"model_a": 2, "model_b": 1, "model_c": 1, "model_d": 1}
        ),
        0.2,
        abs_tol=1e-5,
    )


def test_simple_profiler():
    """A simple test case for SimpleProfiler
    (See: profiler_example.png for visualization)
    """
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

    # test graph dependencies
    graph = profiler.graph
    assert graph["model_a"] == set()
    assert graph["model_b"] == set(["model_a"])
    assert graph["model_c"] == set()
    assert graph["model_d"] == set(["model_a"])
    assert graph["pipeline"] == set(["model_b", "model_c", "model_d"])

    # test graph calls
    graph_calls = profiler.graph_calls
    assert graph_calls["model_a"] == {"__main__": 2}
    assert graph_calls["model_b"] == {"__main__": 1, "model_a": 1}
    assert graph_calls["model_c"] == {"__main__": 1}
    assert graph_calls["model_d"] == {"__main__": 1, "model_a": 1}
    assert graph_calls["pipeline"] == {
        "__main__": 1,
        "model_a": 2,
        "model_b": 1,
        "model_c": 1,
        "model_d": 1,
    }

    # test total durations per model
    total_durations = dict(zip(stat["Name"], stat["Total duration (s)"]))
    assert math.isclose(total_durations["model_a"], 2.0, rel_tol=rel_tol)
    assert math.isclose(total_durations["model_b"], 1.5, rel_tol=rel_tol)
    assert math.isclose(total_durations["model_c"], 0.7, rel_tol=rel_tol)
    assert math.isclose(total_durations["model_d"], 1.1, rel_tol=rel_tol)
    assert math.isclose(total_durations["pipeline"], 3.5, rel_tol=rel_tol)

    # test duration per call per model
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
        profiler.end("debug_end", {})


class ModelX(Model):
    CONFIGURATIONS: Dict[str, Any] = {"model_x": {}}

    def _predict(self, item):
        time.sleep(1)
        return item


class ModelY(Model):
    CONFIGURATIONS: Dict[str, Any] = {
        "model_y": {
            "model_dependencies": {
                "model_x",
            }
        }
    }

    def _load(self):
        self.model_x = self.model_dependencies["model_x"]

    def _predict(self, item):
        item = self.model_x.predict(item)

        time.sleep(0.5)
        return item


class ModelZ(Model):
    CONFIGURATIONS: Dict[str, Any] = {"model_z": {}}

    def _predict(self, item):
        time.sleep(0.7)
        return item


class DynamicModel(Model):
    CONFIGURATIONS: Dict[str, Any] = {
        "dynamic_model": {
            "model_dependencies": {
                "model_x",
                "model_y",
                "model_z",
            }
        }
    }

    def _load(self):
        self.model_x = self.model_dependencies["model_x"]
        self.model_y = self.model_dependencies["model_y"]
        self.model_z = self.model_dependencies["model_z"]

    def _predict(self, item, call_x: bool = False):
        if call_x:
            item = self.model_x.predict(item)
        else:
            # model_x will still be called in model_y
            item = self.model_y.predict(item)
        time.sleep(0.1)
        item = self.model_z(item)
        return item


class DynamicPipeline(Model):
    CONFIGURATIONS: Dict[str, Any] = {
        "dynamic_pipeline": {
            "model_dependencies": {
                "dynamic_model",
            }
        }
    }

    def _load(self):
        self.dynamic_model = self.model_dependencies["dynamic_model"]

    def _predict(self, item):
        """Run "dynamic_model" twice with different argument to simulate
        python caching.

        """
        time.sleep(0.3)
        item = self.dynamic_model(item, call_x=True)
        item = self.dynamic_model(item, call_x=False)
        return item


def test_simple_profiler_dynamic_graph():
    """A more complicated test case with dynamic model.
    A dynamic model has different duration depending on its arguments.
    The dynamic model is used to simulate "caching" in model "predict".
    """
    model_library = ModelLibrary(
        models=[ModelX, ModelY, ModelZ, DynamicModel, DynamicPipeline]
    )
    pipeline = model_library.get("dynamic_pipeline")
    item = {"abc": 123}
    profiler = SimpleProfiler(pipeline)
    _ = pipeline.predict(item)
    stat = profiler.summary()
    assert set(stat["Name"]) == set(
        [
            "model_x",
            "model_y",
            "model_z",
            "dynamic_model",
            "dynamic_pipeline",
        ]
    )

    rel_tol = 0.3
    if platform.system() == "Darwin":
        # Issue: perf_counter result does not count system sleep time in Mac OS
        # - https://bugs.python.org/issue41303
        rel_tol = 0.7

    graph = profiler.graph
    assert graph["model_x"] == set()
    assert graph["model_y"] == set(["model_x"])
    assert graph["model_z"] == set()
    assert graph["dynamic_model"] == set(["model_x", "model_y", "model_z"])
    assert graph["dynamic_pipeline"] == set(["dynamic_model"])

    # test graph calls
    graph_calls = profiler.graph_calls
    assert graph_calls["model_x"] == {"__main__": 2}
    assert graph_calls["model_y"] == {"__main__": 1, "model_x": 1}
    assert graph_calls["model_z"] == {"__main__": 2}
    assert graph_calls["dynamic_model"] == {
        "__main__": 2,
        "model_x": 2,
        "model_y": 1,
        "model_z": 2,
    }
    assert graph_calls["dynamic_pipeline"] == {
        "__main__": 1,
        "dynamic_model": 2,
        "model_x": 2,
        "model_y": 1,
        "model_z": 2,
    }

    # test total durations per model
    total_durations = dict(zip(stat["Name"], stat["Total duration (s)"]))
    assert math.isclose(total_durations["model_x"], 2.0, rel_tol=rel_tol)
    assert math.isclose(total_durations["model_y"], 1.5, rel_tol=rel_tol)
    assert math.isclose(total_durations["model_z"], 1.4, rel_tol=rel_tol)
    assert math.isclose(total_durations["dynamic_model"], 4.1, rel_tol=rel_tol)
    assert math.isclose(total_durations["dynamic_pipeline"], 4.4, rel_tol=rel_tol)

    # test duration per call per model
    model_durations = dict(zip(stat["Name"], stat["Duration per call (s)"]))
    assert math.isclose(model_durations["model_x"], 1.0, rel_tol=rel_tol)
    assert math.isclose(model_durations["model_y"], 1.5, rel_tol=rel_tol)
    assert math.isclose(model_durations["model_z"], 0.7, rel_tol=rel_tol)
    # "dynamic_model" is run twice with different durations
    assert math.isclose(
        model_durations["dynamic_model"], (2.3 + 1.8) / 2, rel_tol=rel_tol
    )  # 2.05
    assert math.isclose(model_durations["dynamic_pipeline"], 4.4, rel_tol=rel_tol)

    # test net durations per call
    net_durations = dict(zip(stat["Name"], stat["Net duration per call (s)"]))
    assert math.isclose(net_durations["model_x"], 1.0, rel_tol=rel_tol)
    assert math.isclose(net_durations["model_y"], 0.5, rel_tol=rel_tol)
    assert math.isclose(net_durations["model_z"], 0.7, rel_tol=rel_tol)
    assert math.isclose(net_durations["dynamic_model"], 0.1, rel_tol=rel_tol)
    assert math.isclose(net_durations["dynamic_pipeline"], 0.3, rel_tol=rel_tol)

    # test number of call
    num_call = dict(zip(stat["Name"], stat["Num call"]))
    assert num_call == {
        "dynamic_pipeline": 1,
        "dynamic_model": 2,
        "model_x": 2,
        "model_y": 1,
        "model_z": 2,
    }

    # test net percentage ()
    assert math.isclose(sum(stat["Net percentage %"]), 100, abs_tol=1.0)

    # test total percentage ~= 100% (decreasing)
    assert math.isclose(stat["Total percentage %"][0], 99.9, abs_tol=1.0)

    # test print table
    table_str = profiler.summary(print_table=True)
    assert isinstance(table_str, str)


def test_simple_profiler_memory_caching():
    """A test case simulating memory caching for SimpleProfiler"""
    model_library = ModelLibrary(models=[ModelA, ModelB, ModelC, ModelD, Pipeline2])
    pipeline = model_library.get("pipeline2")
    item = {"abc": 123}
    profiler = SimpleProfiler(pipeline)
    _ = pipeline.predict(item)
    stat = profiler.summary()

    assert set(stat["Name"]) == set(
        ["pipeline2", "model_b", "model_a", "model_c", "model_d"]
    )

    rel_tol = 0.3
    if platform.system() == "Darwin":
        # Issue: perf_counter result does not count system sleep time in Mac OS
        # - https://bugs.python.org/issue41303
        rel_tol = 0.7

    # test graph dependencies
    graph = profiler.graph
    assert graph["model_a"] == set()
    assert graph["model_b"] == set(["model_a"])
    assert graph["model_c"] == set()
    assert graph["model_d"] == set(["model_a"])
    assert graph["pipeline2"] == set(["model_a", "model_b", "model_c", "model_d"])

    # test graph calls
    graph_calls = profiler.graph_calls
    assert graph_calls["model_a"] == {"__main__": 3}
    assert graph_calls["model_b"] == {"__main__": 1, "model_a": 1}
    assert graph_calls["model_c"] == {"__main__": 1}
    assert graph_calls["model_d"] == {"__main__": 1, "model_a": 1}
    assert graph_calls["pipeline2"] == {
        "__main__": 1,
        "model_a": 3,
        "model_b": 1,
        "model_c": 1,
        "model_d": 1,
    }

    # test total durations per model
    total_durations = dict(zip(stat["Name"], stat["Total duration (s)"]))
    assert math.isclose(total_durations["model_a"], 4.0, rel_tol=rel_tol)
    assert math.isclose(total_durations["model_b"], 1.5, rel_tol=rel_tol)
    assert math.isclose(total_durations["model_c"], 0.7, rel_tol=rel_tol)
    assert math.isclose(total_durations["model_d"], 1.1, rel_tol=rel_tol)
    assert math.isclose(total_durations["pipeline2"], 5.5, rel_tol=rel_tol)

    # test duration per call per model
    model_durations = dict(zip(stat["Name"], stat["Duration per call (s)"]))
    assert math.isclose(model_durations["model_a"], 1.33, rel_tol=rel_tol)
    assert math.isclose(model_durations["model_b"], 1.5, rel_tol=rel_tol)
    assert math.isclose(model_durations["model_c"], 0.7, rel_tol=rel_tol)
    assert math.isclose(model_durations["model_d"], 1.1, rel_tol=rel_tol)
    assert math.isclose(model_durations["pipeline2"], 5.5, rel_tol=rel_tol)

    # test net durations per call
    net_durations = dict(zip(stat["Name"], stat["Net duration per call (s)"]))
    assert math.isclose(net_durations["model_a"], 1.33, rel_tol=rel_tol)
    assert math.isclose(net_durations["model_b"], 0.5, rel_tol=rel_tol)
    assert math.isclose(net_durations["model_c"], 0.7, rel_tol=rel_tol)
    assert math.isclose(net_durations["model_d"], 0.1, rel_tol=rel_tol)
    assert math.isclose(net_durations["pipeline2"], 0.2, rel_tol=rel_tol)

    # test number of call
    num_call = dict(zip(stat["Name"], stat["Num call"]))
    assert num_call == {
        "pipeline2": 1,
        "model_a": 3,
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
