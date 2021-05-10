#!/usr/bin/env python3
# flake8: noqa: E402

import os
import sys

import click

realpath = os.path.realpath(__file__)
dir_realpath = os.path.dirname(os.path.dirname(realpath))
sys.path.append(dir_realpath)

import modelkit.models
from modelkit import cli, load_model
from modelkit.core.model_configuration import configure


@click.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
)
@click.argument("model_asset")
@click.pass_context
def fit(ctx, model_asset):
    kwargs = {ctx.args[i][2:]: ctx.args[i + 1] for i in range(0, len(ctx.args), 2)}
    for param, value in kwargs.items():
        if any(param.endswith(suffix) for suffix in ("cleaner", "vectorizer")):
            kwargs[param] = load_model(value)
    models_configurations = configure(modelkit.models)
    new_model, _ = cli.fit(model_asset, models_configurations, **kwargs)


if __name__ == "__main__":
    fit()
