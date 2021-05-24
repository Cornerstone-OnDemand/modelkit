#!/usr/bin/env python3
# flake8: noqa: E402

import json
import os
import sys

import click
import fastapi
import uvicorn

realpath = os.path.realpath(__file__)
sys.path.append(os.path.dirname(realpath))
dir_realpath = os.path.dirname(os.path.dirname(realpath))
sys.path.append(dir_realpath)

from modelkit.api import ModelkitAutoAPIRouter


@click.group()
def cli():
    pass


@cli.command("serve")
@click.option("--required-models", type=str, multiple=True)
@click.option("--models", type=str, multiple=True)
@click.option("--host", type=str, default="localhost")
@click.option("--port", type=int, default=8000)
def _cli(required_models, models, host, port):
    app = fastapi.FastAPI()
    router = ModelkitAutoAPIRouter(
        required_models=list(required_models) or None,
        models=models,
    )
    app.include_router(router)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    cli()
