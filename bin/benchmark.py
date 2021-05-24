#!/usr/bin/env python3
import json
import logging
import os
import sys
from time import perf_counter, sleep

import click
import humanize
import networkx as nx
from memory_profiler import memory_usage
from networkx.drawing.nx_agraph import write_dot
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from rich.tree import Tree

rootdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
sys.path.append(rootdir)

from modelkit import ModelLibrary  # noqa: E402
from modelkit.core.model_configuration import configure, list_assets  # noqa: E402


@click.group()
def cli_():
    pass


def load_model(m, service):
    service._load(m)
    sleep(1)


def _configure_from_cli_arguments(models, required_models, all):
    models_configurations = configure(models=models)
    if all:
        required_models = list(models_configurations)
    service = ModelLibrary(
        required_models=required_models,
        configuration=models_configurations,
        settings={"lazy_loading": True},
    )
    return service


@cli_.command()
@click.option("--models", "-m", multiple=True)
@click.option("--required-models", "-r", multiple=True)
@click.option("--all", is_flag=True)
def memory(models, required_models, all):
    """
    Show memory consumption of modelkit models
    """
    service = _configure_from_cli_arguments(models, required_models, all)
    grand_total = 0
    stats = {}
    logging.getLogger().setLevel(logging.ERROR)
    if service.required_models:
        with Progress(transient=True) as progress:
            task = progress.add_task("Profiling memory...", total=len(required_models))
            for m in required_models:
                deps = service.configuration[m].model_dependencies
                deps = deps.values() if isinstance(deps, dict) else deps
                for dependency in list(deps) + [m]:
                    mu = memory_usage((load_model, (dependency, service), {}))
                    stats[dependency] = mu[-1] - mu[0]
                    grand_total += mu[-1] - mu[0]
                progress.update(task, advance=1)

    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Model")
    table.add_column("Memory", style="dim")

    for k, (m, mc) in enumerate(stats.items()):
        table.add_row(
            m,
            humanize.naturalsize(mc * 10 ** 6, format="%.2f"),
            end_section=k == len(stats) - 1,
        )
    table.add_row("Total", humanize.naturalsize(grand_total * 10 ** 6, format="%.2f"))
    console.print(table)


@cli_.command()
@click.option("--models", "-m", multiple=True)
@click.option("--required-models", "-r", multiple=True)
@click.option("--all", is_flag=True)
def assets(models, required_models, all):
    """
    List the assets necessary to run a given set of models
    """
    service = _configure_from_cli_arguments(models, required_models, all)

    console = Console()
    if service.configuration:
        for m in service.required_models:
            assets_specs = list_assets(
                configuration=service.configuration, required_models=[m]
            )
            model_tree = Tree(f"[bold]{m}[/bold] ({len(assets_specs)} assets)")
            if assets_specs:
                for asset_spec_string in assets_specs:
                    model_tree.add(asset_spec_string.replace("[", "\["), style="dim")
            console.print(model_tree)


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
@click.option("--models", "-m", multiple=True)
@click.option("--required-models", "-r", multiple=True)
@click.option("--all", is_flag=True)
def dependencies(models, required_models, all):
    """
    Create a DOT file with the dependency graph from a list of assets
    """
    service = _configure_from_cli_arguments(models, required_models, all)
    if service.configuration:
        dependency_graph = nx.DiGraph(overlap="False")
        for m in service.required_models:
            add_dependencies_to_graph(dependency_graph, m, service.configuration)
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
        f"Finished in {sum(times):.1f} s, "
        f"approximately {sum(times)/n*1e3:.2f} ms per call"
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
