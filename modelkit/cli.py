import json
import logging
import os
import sys
from time import perf_counter, sleep

import click
import fastapi
import humanize
import networkx as nx
import uvicorn
from memory_profiler import memory_usage
from networkx.drawing.nx_agraph import write_dot
from rich.console import Console
from rich.progress import Progress, track
from rich.table import Table
from rich.tree import Tree

from modelkit import ModelLibrary
from modelkit.api import ModelkitAutoAPIRouter
from modelkit.assets.cli import assets_cli
from modelkit.core.model_configuration import configure, list_assets
from modelkit.core.models.tensorflow_model import safe_np_dump
from modelkit.utils.tensorflow import deploy_tf_models


@click.group()
def modelkit_cli():
    sys.path.append(os.getcwd())
    pass


modelkit_cli.add_command(assets_cli)


def _configure_from_cli_arguments(models, required_models, all, settings):
    models_configurations = configure(models=models)
    if all:
        required_models = list(models_configurations)
    service = ModelLibrary(
        required_models=required_models,
        configuration=models_configurations,
        settings=settings,
    )
    return service


@modelkit_cli.command()
@click.argument("models", type=str, nargs=-1, required=True)
@click.option("--required-models", "-r", multiple=True)
@click.option("--all", is_flag=True)
def memory(models, required_models, all):
    """
    Show memory consumption of modelkit models.
    """

    def _load_model(m, service):
        service._load(m)
        sleep(1)

    service = _configure_from_cli_arguments(
        models, required_models, all, {"lazy_loading": True}
    )
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
                    mu = memory_usage((_load_model, (dependency, service), {}))
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


@modelkit_cli.command("list-assets")
@click.argument("models", type=str, nargs=-1, required=True)
@click.option("--required-models", "-r", multiple=True)
@click.option("--all", is_flag=True)
def list_assets_cli(models, required_models, all):
    """
    List necessary assets.

    List the assets necessary to run a given set of models.
    """
    service = _configure_from_cli_arguments(
        models, required_models, all, {"lazy_loading": True}
    )

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


@modelkit_cli.command()
@click.argument("models", type=str, nargs=-1, required=True)
@click.option("--required-models", "-r", multiple=True)
@click.option("--all", is_flag=True)
def dependencies_graph(models, required_models, all):
    """
    Create a  dependency graph for a library.

    Create a DOT file with the assets and model dependency graph
    from a list of models.
    """
    service = _configure_from_cli_arguments(
        models, required_models, all, {"lazy_loading": True}
    )
    if service.configuration:
        dependency_graph = nx.DiGraph(overlap="False")
        for m in service.required_models:
            add_dependencies_to_graph(dependency_graph, m, service.configuration)
        write_dot(dependency_graph, "dependencies.dot")


@modelkit_cli.command()
@click.argument("models", type=str, nargs=-1, required=True)
@click.option("--required-models", "-r", multiple=True)
@click.option("--all", is_flag=True)
def describe(models, required_models, all):
    """
    Describe a library.

    Show settings, models and assets for a given library.
    """
    service = _configure_from_cli_arguments(models, required_models, all, {})
    service.describe()


@modelkit_cli.command()
@click.argument("model")
@click.argument("example")
@click.option("--models", type=str, required=True)
@click.option("--n", "-n", default=100)
def time(model, example, models, n):
    """
    Benchmark a model on an example.

    Time n iterations of a model's call on an example.
    """
    service = _configure_from_cli_arguments(
        models, [model], all, {"lazy_loading": True}
    )

    console = Console()

    t0 = perf_counter()
    model = service.get(model)
    console.print(
        f"{f'Loaded model `{model.configuration_key}` in':50} "
        f"... {f'{perf_counter()-t0:.2f} s':>10}"
    )

    example_deserialized = json.loads(example)
    console.print(f"Calling `predict` {n} times on example:")
    console.print(f"{json.dumps(example_deserialized, indent = 2)}")

    times = []
    for _ in track(range(n)):
        t0 = perf_counter()
        model(example_deserialized)
        times.append(perf_counter() - t0)

    console.print(
        f"Finished in {sum(times):.1f} s, "
        f"approximately {sum(times)/n*1e3:.2f} ms per call"
    )

    t0 = perf_counter()
    model([example_deserialized] * n)
    batch_time = perf_counter() - t0
    console.print(
        f"Finished batching in {batch_time:.1f} s, approximately"
        f" {batch_time/n*1e3:.2f} ms per call"
    )


@modelkit_cli.command("serve")
@click.option("--required-models", type=str, multiple=True)
@click.argument("models", type=str, nargs=-1, required=True)
@click.option("--host", type=str, default="localhost")
@click.option("--port", type=int, default=8000)
def serve(required_models, models, host, port):
    """
    Run a library as a service.

    Run an HTTP server with specified models using FastAPI
    """
    app = fastapi.FastAPI()
    router = ModelkitAutoAPIRouter(
        required_models=list(required_models) or None,
        models=models,
    )
    app.include_router(router)
    uvicorn.run(app, host=host, port=port)


@modelkit_cli.command("predict")
@click.argument("model_name", type=str)
@click.argument("models", type=str, nargs=-1, required=True)
def predict(model_name, models):
    """
    Make predictions for a given model.
    """
    svc = _configure_from_cli_arguments(models, [model_name], False, {})
    model = svc.get(model_name)
    while True:
        r = click.prompt(f"[{model_name}]>")
        if r:
            res = model(json.loads(r))
            click.secho(json.dumps(res, indent=2, default=safe_np_dump))


@modelkit_cli.command("tf-serving")
@click.argument("mode", type=click.Choice(["local-docker", "local-process", "remote"]))
@click.option("--models", type=str, required=True)
@click.option("--required-models", "-r", multiple=True)
@click.option("--verbose", is_flag=True)
def tf_serving(mode, models, required_models, verbose):
    service = _configure_from_cli_arguments(
        models, required_models, all, {"lazy_loading": True}
    )

    deploy_tf_models(service, mode, verbose=verbose)
