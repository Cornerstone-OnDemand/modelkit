### SimpleProfiler

The `SimpleProfiler` records `predict` (`predict_batch` or `predict_gen`) time for the model and all its sub-models defined in `model_dependencies` recursively. The model dependencies graph is built in order to profile the net duration of all sub-model. The following code snippet shows the usage of `SimpleProfiler`.

```python
import modelkit
from modelkit.core.profilers.simple import SimpleProfiler

model = modelkit.load_model(...) # load a modelkit model
profiler = SimpleProfiler(model)
res = model(item) # == model.predict(item)
profiler.summary() # return profiling result (Dict) or str

```

The profiling result includes 

- "Name": name of model and its sub-models.
- "Num call" : number of calls for each models.
- "Net duration per call (s)" : duration of model minus the sum of all its direct children defined in `model_dependencies` graph.
- "Net percentage %" : net duration multiplied by the number of calls (represented in percentage)
- "Duration per call (s)" : inference time per call (i.e predict) of each model 
- "Total duration (s)" : total duration of each model
- "Total percentage %" : total duration in term of percentage for each model


!!! Tips
    use `print_table=True` and `tablefmt: str` arguments to return pretty table. See: <https://pypi.org/project/tabulate/> for all available table formats. (p.s latex format included)


See `test_simple_profiler.py` for an example:

<p align="center">
  <a href="https://github.com/Cornerstone-OnDemand/modelkit">
    <img src="https://raw.githubusercontent.com/Cornerstone-OnDemand/modelkit/main/docs/library/profilers/profiler_example.png" alt="graph" width="600" height="300">
  </a>
</p>

```python

print(profiler.summary(print_table=True, tablefmt="github"))

```

| Name     | Net duration per call (s) | Net percentage % | Num call | Duration per call (s) | Total duration (s) | Total percentage % |
| -------- | ------------------------- | ---------------- | -------- | --------------------- | ------------------ | ------------------ |
| pipeline | 0.200144                  | 5.68254          | 1        | 3.52208               | 3.52208            | 99.9998            |
| model_a  | 1.00419                   | 57.0225          | 2        | 1.00419               | 2.00838            | 57.0225            |
| model_b  | 0.504451                  | 14.3225          | 1        | 1.50864               | 1.50864            | 42.8338            |
| model_d  | 0.10479                   | 2.97523          | 1        | 1.10898               | 1.10898            | 31.4865            |
| model_c  | 0.704313                  | 19.997           | 1        | 0.704313              | 0.704313           | 19.997             |