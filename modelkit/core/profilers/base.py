import typing
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Dict, Generator, Set

from modelkit.core.model import AsyncModel, Model, WrappedAsyncModel


class BaseProfiler(ABC):
    """Base Profiler class to be inherited for custom profiler."""

    def __init__(self, model: Model) -> None:
        self.model = model
        self.main_model_name = self.model.configuration_key
        self._build(self.model)

    @abstractmethod
    def start(self, model_name: str) -> None:
        """Define how to start recording an action."""

    @abstractmethod
    def end(self, model_name: str) -> None:
        """Define how to record the cost when an action is completed."""

    def summary(self, *args, **kwargs) -> str:  # type: ignore
        """Summary function to be overwritten"""
        return ""

    @contextmanager
    def profile(self, *args, **kwargs) -> Generator:  # type: ignore
        """Override this function for your custom profiler.

        Example:
            try:
                self.start(model_name)
                yield model_name
            finally:
                self.end(model_name)
        Usage:
            with self.profile('do something'):
                # do something
        """
        raise NotImplementedError

    def _build(self, model: typing.Union[Model, AsyncModel, WrappedAsyncModel]):
        """setattr 'profiler' to all sub-models via "model_dependencies" recursively"""
        model.profiler = self  # type: ignore
        if isinstance(model, WrappedAsyncModel):
            # let's work on the wrapped model instead of the wrapper
            model = model.async_model
        for model_dependency in model.model_dependencies.values():
            self._build(model_dependency)

    def _build_graph(
        self,
        model: typing.Union[Model, AsyncModel, WrappedAsyncModel],
        graph: Dict[str, Set],
    ) -> Dict[str, Set]:
        """Build the model dependency graph in order to compute net cost of all
        sub models. graph[model_name] gives the set of all (direct) sub model names.
        """
        if isinstance(model, WrappedAsyncModel):
            # let's work on the wrapped model instead of the wrapper
            model = model.async_model
        name = model.configuration_key
        children = set()
        for key in model.model_dependencies:
            children.add(key)
            graph = self._build_graph(model.model_dependencies[key], graph)
        graph[name] = children  # type: ignore
        return graph
