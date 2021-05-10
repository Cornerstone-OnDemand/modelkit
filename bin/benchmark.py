#!/usr/bin/env python3
# flake8: noqa: E402
import importlib
import json
import os
import sys
from time import perf_counter, sleep

import click
import networkx as nx
from memory_profiler import memory_usage
from networkx.drawing.nx_agraph import write_dot

rootdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
sys.path.append(rootdir)

import modelkit
import modelkit.models
from modelkit import ModelLibrary
from modelkit.core.model_configuration import configure, list_assets


@click.group()
def cli_():
    pass


def load_model(m, service):
    service._load(m)
    sleep(1)


@cli_.command()
@click.option("--model", "-m", multiple=True)
@click.option("--all", is_flag=True)
def memory(model, all):
    """
    Show memory consumption of modelkit models
    """
    models_configurations = configure()
    if all:
        model = list(models_configurations)
    service = ModelLibrary(required_models=[])
    grand_total = 0
    stats = {}
    if model:
        click.secho(f"Profiling memory for model: {' '.join(model)}")
        for m in model:
            deps = models_configurations[m].model_dependencies
            deps = deps.values() if isinstance(deps, dict) else deps
            for dependency in list(deps) + [m]:
                mu = memory_usage((load_model, (dependency, service), {}))
                stats[dependency] = mu[-1] - mu[0]
                grand_total += mu[-1] - mu[0]

        click.secho(f"{'* Models':10}" + "-" * 55)
        for m, mc in stats.items():
            click.secho(f"{m:50} ... {f'{mc:.2f} MB':>10}")

    click.secho("-" * 65)
    click.secho(f"{'Total':50} ... {f'{grand_total:.2f} MB':>10}")


@cli_.command()
@click.option("--model", "-m", multiple=True)
@click.option("--all", is_flag=True)
@click.option("--module", multiple=True, default=["modelkit.models"])
def assets(model, all, module):
    """
    List the assets necessary to run a given set of models
    """
    models_configurations = configure(
        [importlib.import_module(model_module) for model_module in module]
    )
    if all:
        model = list(models_configurations)
    service = ModelLibrary(required_models=[])
    if model:
        for asset_spec_string in list_assets(
            configuration=models_configurations, required_models=model
        ):
            click.secho(asset_spec_string)


def add_dependencies_to_graph(g, model, configurations):
    g.add_node(
        model,
        type="model",
        fillcolor="/accent3/2",
        style="filled",
        shape="box",
    )
    model_configuration = configurations[model]
    if model_configuration.asset:
        g.add_node(
            model_configuration.asset,
            type="asset",
            fillcolor="/accent3/3",
            style="filled",
        )
        g.add_edge(model, model_configuration.asset)
    for dependent_model in model_configuration.model_dependencies:
        g.add_edge(model, dependent_model)
        add_dependencies_to_graph(g, dependent_model, configurations)


@cli_.command()
@click.option("--model", "-m", multiple=True)
@click.option("--all", is_flag=True)
@click.option("--module", multiple=True, default=["modelkit.models"])
def dependency_graph(model, all, module):
    """
    Create a DOT file with the dependency graph from a list of assets
    """
    models_configurations = configure(
        [importlib.import_module(model_module) for model_module in module]
    )
    if all:
        model = list(models_configurations)
    service = ModelLibrary(required_models=[])
    if model:
        dependency_graph = nx.DiGraph(overlap="False")
        for m in model:
            add_dependencies_to_graph(dependency_graph, m, models_configurations)
        write_dot(dependency_graph, "dependencies.dot")


@cli_.command()
@click.argument("model")
@click.argument("example")
@click.option("-n", default=100)
def time(model, example, n):
    """
    Time n iterations of a model's predict on an example
    """
    service = ModelLibrary(required_models=[model])

    t0 = perf_counter()
    model = service.get_model(model)
    print(f"{f'Loaded model `{model}` in':50} ... {f'{perf_counter()-t0:.2f} s':>10}")

    example_deserialized = json.loads(example)
    print(f"Calling `predict` {n} times on example:")
    print(f"{json.dumps(example_deserialized, indent = 2)}")

    times = []
    for _ in range(n):
        t0 = perf_counter()
        model.predict(example_deserialized)
        times.append(perf_counter() - t0)

    print(
        f"Finished in {sum(times):.1f} s, approximately {sum(times)/n*1e3:.2f} ms per call"
    )

    t0 = perf_counter()
    model.predict([example_deserialized] * n)
    batch_time = perf_counter() - t0
    print(
        f"Finished batching in {batch_time:.1f} s, approximately"
        f" {batch_time/n*1e3:.2f} ms per call"
    )


if __name__ == "__main__":
    cli_()
