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
from modelkit.assets.remote import StorageProvider
from modelkit.assets.settings import AssetSpec


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
        manager.storage_provider.driver.download_object(
            object_name=parsed_path["object_name"],
            destination_path=asset_path,
        )
    except ObjectDoesNotExistError:
        # maybe prefix containing objects
        paths = [
            path
            for path in manager.storage_provider.driver.iterate_objects(
                prefix=parsed_path["object_name"]
            )
        ]
        if not paths:
            raise

        os.mkdir(asset_path)
        for path in paths:
            object_name = path.split("/")[-1]
            manager.storage_provider.driver.download_object(
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
@click.option("--storage-prefix", envvar="MODELKIT_STORAGE_PREFIX")
@click.option("--dry-run", is_flag=True)
def new(asset_path, asset_spec, storage_prefix, dry_run):
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
    manager = StorageProvider(
        prefix=storage_prefix,
    )
    print("Current assets manager:")
    print(f" - storage provider = `{manager.driver}`")
    print(f" - prefix = `{storage_prefix}`")

    print(f"Current asset: `{asset_spec}`")
    spec = AssetSpec.from_string(asset_spec)
    version = spec.versioning.get_initial_version()
    print(f" - name = `{spec.name}`")

    print(f"Push a new asset `{spec.name}` " f"with version `{version}`?")

    response = click.prompt("[y/N]")
    if response == "y":
        with tempfile.TemporaryDirectory() as tmp_dir:
            if asset_path.startswith("gs://"):
                asset_path = _download_object_or_prefix(
                    manager, asset_path=asset_path, destination_dir=tmp_dir
                )
            manager.new(asset_path, spec.name, version, dry_run)
    else:
        print("Aborting.")


@assets_cli.command("update")
@click.argument("asset_path")
@click.argument("asset_spec")
@click.option(
    "--bump-major",
    is_flag=True,
    help="[minor-major] Push a new major version (1.0, 2.0, etc.)",
)
@click.option("--storage-prefix", envvar="MODELKIT_STORAGE_PREFIX")
@click.option("--dry-run", is_flag=True)
def update(asset_path, asset_spec, storage_prefix, bump_major, dry_run):
    """
    Update an existing asset using versioning system
    set in MODELKIT_ASSETS_VERSIONING_SYSTEM (major/minor by default)

    Update an existing asset ASSET_SPEC with ASSET_PATH file.


    By default will upload a new minor version.

    ASSET_PATH is the path to the file. The file can be local remote (AWS or GCS)
    (starting with gs:// or s3://)

    ASSET_SPEC is and asset specification of the form
    [asset_name]:[version]

    Specific documentation depends on the choosen model
    """

    _check_asset_file_number(asset_path)
    manager = StorageProvider(
        prefix=storage_prefix,
    )

    print("Current assets manager:")
    print(f" - storage provider = `{manager.driver}`")
    print(f" - prefix = `{storage_prefix}`")

    print(f"Current asset: `{asset_spec}`")
    versioning_system = os.environ.get(
        "MODELKIT_ASSETS_VERSIONING_SYSTEM", "major_minor"
    )
    spec = AssetSpec.from_string(asset_spec, versioning=versioning_system)
    print(f" - versioning system = `{versioning_system}` ")
    print(f" - name = `{spec.name}`")
    print(f" - version = `{spec.version}`")

    try:
        version_list = manager.get_versions_info(spec.name)
    except ObjectDoesNotExistError:
        print("Remote asset not found. Create it first using `new`")
        sys.exit(1)

    update_params = spec.versioning.get_update_cli_params(
        version=spec.version,
        version_list=version_list,
        bump_major=bump_major,
    )

    print(update_params["display"])
    new_version = spec.versioning.increment_version(
        spec.sort_versions(version_list),
        update_params["params"],
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
                name=spec.name,
                version=new_version,
                dry_run=dry_run,
            )
    else:
        print("Aborting.")


@assets_cli.command("list")
@click.option("--storage-prefix", envvar="MODELKIT_STORAGE_PREFIX")
def list(storage_prefix):
    """lists all available assets and their versions."""
    manager = StorageProvider(
        prefix=storage_prefix,
    )

    console = Console()
    tree = Tree("[bold]Assets store[/bold]")
    tree.add(f"[dim]storage provider[/dim] {manager.driver.__class__.__name__}")
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
