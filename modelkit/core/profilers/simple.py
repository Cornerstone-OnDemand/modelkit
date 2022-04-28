import time
from collections import OrderedDict, defaultdict
from contextlib import contextmanager
from typing import Dict, Generator, List, Set, Union

from tabulate import tabulate

from modelkit.core.model import Model
from modelkit.core.profilers.base import BaseProfiler


class SimpleProfiler(BaseProfiler):
    """This simple profiler records the duration of model prediction in seconds,
    and compute the net percentage duration of each sub models via 'model_dependencies'.
    Usage:
        model = modelkit.load_model(...)
        profiler = SimpleProfiler(model)
        res = model(item)
        profiler.summary() # return profiling result (Dict) or str

    Attributes:
        recording_hook (Dict[str, float]): record start/end time of each model call
        durations (List[float]): record duration of each model call
        net_durations (List[float]): record net duration of each model call. Net
            duration is the duration minus all the other sub models' duration.
        graph (Dict[str, Set]): model dependencies graph, get all direct children names
            (Set[str])
        graph_calls (Dict[str, Dict[str, int]]): record all model calls
            e.g
            {
                "pipeline": {
                    "__main__": 1, # "pipeline" is called once
                    "model_a": 2,
                    "model_b": 1,
                    "model_c": 1,
                }
            }
    See test_simple_profiler.py for more details.
    """

    def __init__(self, model: Model) -> None:
        super().__init__(model)
        self.recording_hook: Dict[str, float] = {}
        self.durations = defaultdict(list)  # type: ignore
        self.net_durations = defaultdict(list)  # type: ignore
        graph: Dict[str, Set] = defaultdict(set)
        self.graph = self._build_graph(self.model, graph)
        self.graph_calls: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

    def start(self, model_name: str) -> None:
        if model_name in self.recording_hook:
            raise ValueError(
                f"Attempting to start {model_name} which has already started."
            )
        self.recording_hook[model_name] = time.perf_counter()

    def end(  # type: ignore
        self, model_name: str, sub_calls: Dict[str, int]  # type: ignore
    ) -> None:  # type: ignore
        end_time = time.perf_counter()
        if model_name not in self.recording_hook:
            raise ValueError(f"Attempting to end {model_name} which was never started.")
        start_time = self.recording_hook.pop(model_name)
        duration = end_time - start_time
        self.durations[model_name].append(duration)
        net_duration = self._calculate_net_cost(duration, sub_calls)
        self.net_durations[model_name].append(net_duration)

    @contextmanager
    def profile(self, model_name: str) -> Generator:  # type: ignore
        if model_name == self.main_model_name:
            self.start_time = time.perf_counter()
        previous_calls = self._get_current_sub_calls(model_name)
        try:
            self.start(model_name)
            yield model_name
        finally:
            sub_calls = self._compute_sub_calls_and_update_graph_calls(
                model_name, previous_calls
            )
            self.end(model_name, sub_calls)
            if model_name == self.main_model_name:
                self.total_duration = time.perf_counter() - self.start_time

    def summary(  # type: ignore
        self, *args, print_table: bool = False, **kwargs  # type: ignore
    ) -> Union[Dict[str, List], str]:  # type: ignore
        """Usage

            stat: Dict[str, List] = profiler.summary()
        or
            print(profiler.summary(print_table=True, tablefmt="fancy_grid"))

        See: https://pypi.org/project/tabulate/ for all available table formats.

        """
        result = defaultdict(list)
        total = self.total_duration
        for model_name in self.durations:
            durations = self.durations[model_name]
            result["Name"].append(model_name)
            result["Duration per call (s)"].append(
                sum(durations) / len(durations) if durations else 0
            )
            result["Num call"].append(len(durations))
            result["Total duration (s)"].append(sum(durations))
            result["Total percentage %"].append(100 * sum(durations) / total)
            net_durations = self.net_durations[model_name]
            result["Net duration per call (s)"].append(
                sum(net_durations) / len(net_durations) if net_durations else 0
            )
        result["Net percentage %"] = [
            100 * net * num / total
            for net, num in zip(result["Net duration per call (s)"], result["Num call"])
        ]
        # re-order columns names & sort by "Total percentage %"
        arg_index = sorted(
            range(len(result["Name"])),
            key=result["Total percentage %"].__getitem__,
            reverse=True,
        )
        result_sorted = OrderedDict()
        for col in [
            "Name",
            "Net duration per call (s)",
            "Net percentage %",
            "Num call",
            "Duration per call (s)",
            "Total duration (s)",
            "Total percentage %",
        ]:
            result_sorted[col] = [*map(lambda x: result[col][x], arg_index)]

        if print_table:
            return tabulate(result_sorted, headers="keys", **kwargs)
        return result_sorted

    def _get_current_sub_calls(self, model_name: str) -> Dict[str, int]:
        """Get the number of current sub model calls.
        Args:
            model_name (str)
        Returns:
            Dict[str, int]: sub model calls
        """
        current_calls: Dict[str, int] = {}
        for sub_model in self._get_all_subs(model_name):
            current_calls[sub_model] = self.graph_calls[sub_model]["__main__"]
        return current_calls

    def _get_all_subs(self, model_name: str) -> Set[str]:
        """Get the set of all sub model names."""
        res = set()
        for key in self.graph[model_name]:
            if key != "__main__":
                res.add(key)
            res = res.union(self._get_all_subs(key))
        return res

    def _compute_sub_calls_and_update_graph_calls(
        self, model_name: str, previous_calls: Dict[str, int]
    ) -> Dict[str, int]:
        """Infer all sub models call (`sub_calls`) using `previous_calls` and update
        `graph_calls` and the end of context manager.

        P.S With the 'shared' context manager, we can't directly record `sub_calls`,
            but only the current model call (incremented in
            self.graph_calls[model_name]["__main__"]).
            Using the counts in "__main__" of all models, we deduce all sub models
            calls.

        Args:
            model_name (str): current model name
            previous_calls (Dict[str, int]):

        Returns:
            Dict[str, int]: sub_calls
        """
        self.graph_calls[model_name]["__main__"] += 1
        sub_calls: Dict[str, int] = {}
        for sub_model in self._get_all_subs(model_name):
            sub_calls[sub_model] = self.graph_calls[sub_model][
                "__main__"
            ] - previous_calls.get(sub_model, 0)
            self.graph_calls[model_name][sub_model] += sub_calls[sub_model]
        return sub_calls

    def _calculate_net_cost(self, duration: float, sub_calls: Dict[str, int]) -> float:
        """Compute net cost of each sub models. Subtracting model "duration" by
        "duration" of all direct sub model.

        Args:
            duration (float): model duration
            sub_calls (Dict[str, int]): number of calls of all sub_model

        Returns:
            float: net cost
        """
        net_duration = duration
        for sub_model, num_calls in sub_calls.items():
            if sub_model == "__main__":
                continue
            if num_calls > 0:
                net_duration -= sum(self.net_durations[sub_model][-num_calls:])
        return net_duration
