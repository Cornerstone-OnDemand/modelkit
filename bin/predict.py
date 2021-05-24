#!/usr/bin/env python3
# flake8: noqa: E402

import json
import os
import sys

import click

realpath = os.path.realpath(__file__)
dir_realpath = os.path.dirname(os.path.dirname(realpath))
sys.path.append(dir_realpath)

from modelkit.library import load_model
from modelkit.utils.serializers import safe_np_dump


@click.command()
@click.argument("model_name", type=str)
def cli(model_name):
    p = load_model(model_name)
    while True:
        r = click.prompt(f"[{model_name}]>")
        if r:
            res = p.predict(json.loads(r))
            click.secho(json.dumps(res, indent=2, default=safe_np_dump))


if __name__ == "__main__":
    cli()
