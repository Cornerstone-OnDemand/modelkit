import glob
import os
import re
import sys
import tempfile

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn
from rich.table import Table
from rich.tree import Tree

from modelkit.assets.errors import ObjectDoesNotExistError
from modelkit.assets.manager import AssetsManager
from modelkit.assets.remote import RemoteAssetsStore
from modelkit.assets.settings import AssetSpec, DriverSettings
from modelkit.assets.versioning import (
    filter_versions,
    increment_version,
    parse_version,
    sort_versions,
)


@click.group("assets")
def assets_cli():
    """
    Assets management commands
    """
    pass


gcs_fn_re = r"gs://(?P<bucket_name>[\w\-]+)/(?P<object_name>.+)"


def parse_gcs(path):
    match = re.match(gcs_fn_re, path)
    if not match:
        raise ValueError(f"Could not parse GCS path `{path}`")
    return match.groupdict()


def _download_object_or_prefix(manager, asset_path, destination_dir):
    parsed_path = parse_gcs(asset_path)
    asset_path = os.path.join(destination_dir, "myasset")
    try:
        manager.remote_assets_store.driver.download_object(
            object_name=parsed_path["object_name"],
            destination_path=asset_path,
        )
    except ObjectDoesNotExistError:
        # maybe prefix containing objects
        paths = [
            path
            for path in manager.remote_assets_store.driver.iterate_objects(
                prefix=parsed_path["object_name"]
            )
        ]
        if not paths:
            raise

        os.mkdir(asset_path)
        for path in paths:
            object_name = path.split("/")[-1]
            manager.remote_assets_store.driver.download_object(
                object_name=parsed_path["object_name"] + "/" + object_name,
                destination_path=os.path.join(asset_path, object_name),
            )
    return asset_path


def _check_asset_file_number(asset_path):
    n_files = len(
        [f for f in glob.iglob(os.path.join(asset_path, "**/*"), recursive=True)]
    )
    if n_files > 50:
        click.secho(
            "It looks like you are attempting to push an asset with more than 50 files"
            f" in it ({n_files}).\n"
            "This can lead to poor performance when retrieving the asset, and should"
            " be avoided.\n"
            "You should consider archiving and compressing it.",
            fg="red",
        )
        if click.confirm("Proceed anyways ?", abort=True):
            pass


@assets_cli.command("new")
@click.argument("asset_path")
@click.argument("asset_spec")
@click.option("--bucket", envvar="MODELKIT_STORAGE_BUCKET")
@click.option("--storage-prefix", envvar="MODELKIT_STORAGE_PREFIX")
@click.option("--dry-run", is_flag=True)
def new(asset_path, asset_spec, bucket, storage_prefix, dry_run):
    """
    Create a new asset.

    Create a new asset ASSET_SPEC with ASSET_PATH file.

    Will fail if asset exists (in this case use `update`).

    ASSET_PATH is the path to the file. The file can be local or on GCS
    (starting with gs://)

    ASSET_SPEC is and asset specification of the form
    [asset_name] (Major/minor version information is ignored)

    NB: [asset_name] can contain `/` too.
    """
    _check_asset_file_number(asset_path)
    manager = RemoteAssetsStore(
        storage_prefix=storage_prefix,
        driver=DriverSettings(bucket=bucket),
    )
    print("Current assets manager:")
    print(f" - storage provider = `{manager.driver}`")
    print(f" - bucket = `{bucket}`")
    print(f" - prefix = `{storage_prefix}`")

    print(f"Current asset: `{asset_spec}`")
    spec = AssetSpec.from_string(asset_spec)
    print(f" - name = `{spec.name}`")

    print(f"Push a new asset `{spec.name}` with version `0.0`?")

    response = click.prompt("[y/N]")
    if response == "y":
        with tempfile.TemporaryDirectory() as tmp_dir:
            if asset_path.startswith("gs://"):
                asset_path = _download_object_or_prefix(
                    manager, asset_path=asset_path, destination_dir=tmp_dir
                )
            manager.new(asset_path, spec.name, dry_run)
    else:
        print("Aborting.")


@assets_cli.command("update")
@click.argument("asset_path")
@click.argument("asset_spec")
@click.option(
    "--bump-major", is_flag=True, help="Push a new major version (1.0, 2.0, etc.)"
)
@click.option("--bucket", envvar="MODELKIT_STORAGE_BUCKET")
@click.option("--storage-prefix", envvar="MODELKIT_STORAGE_PREFIX")
@click.option("--dry-run", is_flag=True)
def update(asset_path, asset_spec, bucket, storage_prefix, bump_major, dry_run):
    """
    Update an existing asset.

    Update an existing asset ASSET_SPEC with ASSET_PATH file.

    By default will upload a new minor version.

    ASSET_PATH is the path to the file. The file can be local or on GCS
    (starting with gs://)

    ASSET_SPEC is and asset specification of the form
    [asset_name]:[major_version]
    Minor version information is ignored.

    Examples:

    - Bumping the minor version: assuming modelkit/sentence_piece has versions 0.1, 1.1,
    running

        $ assets update /path/to/vectorizer modelkit/vectorizer:1

    will add a version 1.2

    - Bumping the major version: assuming modelkit/sentence_piece has versions 0.1, 1.0,
    running

        $ assets update /path/to/vectorizer modelkit/vectorizer:1 --bump-major

    will add a version 2.0

    - Bumping the minor version of an older asset: assuming modelkit/sentence_piece has
    versions 0.1, 1.0, running

        $ assets update /path/to/vectorizer modelkit/vectorizer:0

    will add a version 0.2
    """
    _check_asset_file_number(asset_path)
    manager = RemoteAssetsStore(
        storage_prefix=storage_prefix,
        driver=DriverSettings(bucket=bucket),
    )

    print("Current assets manager:")
    print(f" - storage provider = `{manager.driver}`")
    print(f" - bucket = `{bucket}`")
    print(f" - prefix = `{storage_prefix}`")

    print(f"Current asset: `{asset_spec}`")
    spec = AssetSpec.from_string(asset_spec)
    print(f" - name = `{spec.name}`")
    print(f" - major version = `{spec.major_version}`")
    print(f" - minor version (ignored) = `{spec.minor_version}`")

    try:
        versions_list = manager.get_versions_info(spec.name)
    except ObjectDoesNotExistError:
        print("Remote asset not found. Create it first using `new`")
        sys.exit(1)

    major_versions = {parse_version(v)[0] for v in versions_list}
    print(
        f"Found a total of {len(versions_list)} versions "
        f"({len(major_versions)} major versions) "
        f"for `{spec.name}`"
    )
    for major_version in sorted(major_versions):
        print(
            f" - major `{major_version}` = "
            + ", ".join(filter_versions(versions_list, major=str(major_version)))
        )

    new_version = increment_version(
        sort_versions(versions_list), major=spec.major_version, bump_major=bump_major
    )
    print(f"Push a new asset version `{new_version}` " f"for `{spec.name}`?")

    response = click.prompt("[y/N]")
    if response == "y":

        with tempfile.TemporaryDirectory() as tmp_dir:
            if asset_path.startswith("gs://"):
                asset_path = _download_object_or_prefix(
                    manager, asset_path=asset_path, destination_dir=tmp_dir
                )
            manager.update(
                asset_path,
                spec.name,
                bump_major=bump_major,
                major=spec.major_version,
                dry_run=dry_run,
            )
    else:
        print("Aborting.")


@assets_cli.command("list")
@click.option("--bucket", envvar="MODELKIT_STORAGE_BUCKET")
@click.option("--storage-prefix", envvar="MODELKIT_STORAGE_PREFIX")
def list(bucket, storage_prefix):
    """lists all available assets and their versions."""
    manager = RemoteAssetsStore(
        storage_prefix=storage_prefix,
        driver=DriverSettings(bucket=bucket),
    )

    console = Console()
    tree = Tree("[bold]Assets store[/bold]")
    tree.add(f"[dim]storage provider[/dim] {manager.driver.__class__.__name__}")
    tree.add(f"[dim]bucket[/dim] {bucket}")
    tree.add(f"[dim]prefix[/dim] {storage_prefix}")
    console.print(tree)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Asset name")
    table.add_column("Versions", style="dim")

    n = 0
    n_versions = 0
    with Progress(
        SpinnerColumn(), "[progress.description]{task.description}", transient=True
    ) as progress:
        progress.add_task("Listing remote assets", start=False)
        for asset_name, versions_list in manager.iterate_assets():
            table.add_row(asset_name, " ".join(versions_list))
            n += 1
            n_versions += len(versions_list)

    console.print(table)
    console.print(f"Found {n} assets ({n_versions} different versions)")


@assets_cli.command("fetch")
@click.argument("asset")
@click.option("--download", is_flag=True)
def fetch_asset(asset, download):
    """Fetch an asset and download if necessary"""
    manager = AssetsManager()

    info = manager.fetch_asset(asset, return_info=True, force_download=download)

    console = Console()
    console.print(info)
