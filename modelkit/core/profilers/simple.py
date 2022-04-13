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
    """

    def __init__(self, model: Model) -> None:
        super().__init__(model)
        self.recording_hook: Dict[str, float] = {}
        self.durations = defaultdict(list)  # type: ignore

    def start(self, model_name: str) -> None:
        if model_name in self.recording_hook:
            raise ValueError(
                f"Attempting to start {model_name} which has already started."
            )
        self.recording_hook[model_name] = time.perf_counter()

    def end(self, model_name: str) -> None:
        end_time = time.perf_counter()
        if model_name not in self.recording_hook:
            raise ValueError(f"Attempting to end {model_name} which was never started.")
        start_time = self.recording_hook.pop(model_name)
        duration = end_time - start_time
        self.durations[model_name].append(duration)

    @contextmanager
    def profile(self, model_name: str) -> Generator:  # type: ignore
        try:
            if model_name == self.main_model_name:
                self.start_time = time.perf_counter()
            self.start(model_name)
            yield model_name
        finally:
            self.end(model_name)
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
        graph: Dict[str, Set] = defaultdict(set)
        graph = self._build_graph(self.model, graph)
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
        result["Net duration per call (s)"] = self._calculate_net_cost(
            result["Name"], result["Duration per call (s)"], graph
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

    def _calculate_net_cost(
        self, model_names: List[str], model_costs: List[float], graph: Dict[str, Set]
    ) -> List[float]:
        """Compute net cost of each sub models.
        Args:
            model_names (List[str]): list of model name
            model_costs (List[float]): cost of each model
            graph (Dict[str, Set]): graph[model_name] = set of direct sub model names

        Returns:
            List[float]: net cost
        """
        result = []
        data = dict(zip(model_names, model_costs))
        for model_name in model_names:
            result.append(
                max(
                    data[model_name]
                    - sum(data.get(sub_model, 0) for sub_model in graph[model_name]),
                    0,
                )
            )
        return result
