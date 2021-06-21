import os

from structlog import get_logger

from modelkit.assets.manager import AssetsManager
from modelkit.assets.settings import AssetSpec
from modelkit.core.library import download_assets
from modelkit.core.models.tensorflow_model import TensorflowModel

logger = get_logger(__name__)


def write_config(destination, models, verbose=False):
    with open(destination, "w") as f:
        f.write("model_config_list: {\n")
        for m, pth in models.items():
            f.write("    config: {\n")
            f.write(f'        name: "{m}", \n')
            f.write(f'        base_path: "{pth}",\n')
            f.write('        model_platform: "tensorflow"\n')
            f.write("    },\n")
        f.write("}")
    if verbose:
        with open(destination) as f:
            print(f.read())


def deploy_tf_models(lib, mode, config_name="config", verbose=False):
    manager = AssetsManager()
    configuration = lib.configuration
    model_paths = {}
    for model_name in lib.required_models:
        model_configuration = configuration[model_name]
        if not issubclass(model_configuration.model_type, TensorflowModel):
            logger.debug(f"Skipping non TF model `{model_name}`")
            continue
        if not model_configuration.asset:
            raise ValueError(f"TensorFlow model `{model_name}` does not have an asset")
        spec = AssetSpec.from_string(model_configuration.asset)
        if mode == "local-docker":
            model_paths[model_name] = os.path.join(
                "/config",
                f"{spec.name}/{spec.major_version}.{spec.minor_version}",
            )
        elif mode == "local-process":
            model_paths[model_name] = os.path.join(
                manager.assets_dir,
                f"{spec.name}/{spec.major_version}.{spec.minor_version}",
            )
        elif mode == "remote":
            object_name = manager.get_object_name(
                spec.name, f"{spec.major_version}.{spec.minor_version}"
            )
            model_paths[model_name] = f"gs://{manager.bucket}/{object_name}"
        if spec.sub_part:
            model_paths[model_name] += spec.sub_part

    if mode == "local-docker" or mode == "local-process":
        logger.info("Checking that local models are present.")
        download_assets(
            configuration=configuration, required_models=lib.required_models
        )
        target = os.path.join(manager.assets_dir, f"{config_name}.config")

    if model_paths:
        logger.info(
            "Writing TF serving configuration locally.",
            config_name=config_name,
            target=target,
        )
        write_config(target, model_paths, verbose=verbose)
    else:
        logger.info(
            "Nothing to write",
            config_name=config_name,
            target=target,
        )
