## Profilers

In order to analyze/benchmark model inference time, custom profiler can be defined by inheriting `BaseProfiler`. The following functions need to be overwritten: 

- `summary(self, *args, **kwargs)` : define how to print the result
- `start(self, model_name)` : define how to start recording
- `end(self, model_name)` : define how to end recording
- `profile(self, *args, **kwargs)` : (context manager) define how to compute elapsed time


Here, we implement `SimpleProfiler` that uses a simple context manager to profile each call of `predict(...)` by models and its sub-models defined in `model_dependencies` as an exameple. More sophisticated profiler that records CPU, RAM usages could be implemented using `cProfile` and `pstats`.


