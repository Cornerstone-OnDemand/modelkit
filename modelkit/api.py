import os
from typing import Any, Dict, List, Optional, Union

import fastapi
from rich.console import Console
from structlog import get_logger

from modelkit.core.errors import ModelsNotFound
from modelkit.core.library import LibrarySettings, ModelConfiguration, ModelLibrary
from modelkit.core.model import AbstractModel, AsyncModel
from modelkit.core.types import LibraryModelsType

logger = get_logger(__name__)


class ModelkitAPIRouter(fastapi.APIRouter):
    def __init__(
        self,
        # ModelLibrary arguments
        settings: Optional[Union[Dict, LibrarySettings]] = None,
        assetsmanager_settings: Optional[dict] = None,
        configuration: Optional[
            Dict[str, Union[Dict[str, Any], ModelConfiguration]]
        ] = None,
        models: Optional[LibraryModelsType] = None,
        required_models: Optional[Union[List[str], Dict[str, Any]]] = None,
        # APIRouter arguments
        **kwargs,
    ) -> None:
        # add custom startup/shutdown events
        on_startup = kwargs.pop("on_startup", [])
        # on_startup.append(self._on_startup)
        kwargs["on_startup"] = on_startup
        on_shutdown = kwargs.pop("on_shutdown", [])
        on_shutdown.append(self._on_shutdown)
        kwargs["on_shutdown"] = on_shutdown
        super().__init__(**kwargs)

        self.lib = ModelLibrary(
            required_models=required_models,
            settings=settings,
            assetsmanager_settings=assetsmanager_settings,
            configuration=configuration,
            models=models,
        )

    async def _on_shutdown(self):
        await self.lib.aclose()


class ModelkitAutoAPIRouter(ModelkitAPIRouter):
    def __init__(
        self,
        # ModelLibrary arguments
        required_models: Optional[List[str]] = None,
        settings: Optional[Union[Dict, LibrarySettings]] = None,
        assetsmanager_settings: Optional[dict] = None,
        configuration: Optional[
            Dict[str, Union[Dict[str, Any], ModelConfiguration]]
        ] = None,
        models: Optional[LibraryModelsType] = None,
        # paths overrides change the configuration key into a path
        route_paths: Optional[Dict[str, str]] = None,
        # APIRouter arguments
        **kwargs,
    ) -> None:
        super().__init__(
            required_models=required_models,
            settings=settings,
            assetsmanager_settings=assetsmanager_settings,
            configuration=configuration,
            models=models,
            **kwargs,
        )

        route_paths = route_paths or {}
        for model_name in self.lib.required_models:
            m: AbstractModel = self.lib.get(model_name)
            if not isinstance(m, AbstractModel):
                continue
            path = route_paths.get(model_name, "/predict/" + model_name)
            batch_path = route_paths.get(model_name, "/predict/batch/" + model_name)

            summary = ""
            description = ""
            if m.__doc__:
                doclines = m.__doc__.strip().split("\n")
                summary = doclines[0]
                if len(doclines) > 1:
                    description = "".join(doclines[1:])

            console = Console(no_color=True)
            with console.capture() as capture:
                t = m.describe()
                console.print(t)
            description += "\n\n```" + str(capture.get()) + "```"

            logger.info("Adding model", name=model_name)
            item_type = m._item_type or Any
            try:
                item_type.schema()  # type: ignore
            except (ValueError, AttributeError):
                logger.info(
                    "Discarding item type info for model", name=model_name, path=path
                )
                item_type = Any

            self.add_api_route(
                path,
                self._make_model_endpoint_fn(m, item_type),
                methods=["POST"],
                description=description,
                summary=summary,
                tags=[str(type(m).__module__)],
            )
            self.add_api_route(
                batch_path,
                self._make_batch_model_endpoint_fn(m, item_type),
                methods=["POST"],
                description=description,
                summary=summary,
                tags=[str(type(m).__module__)],
            )
            logger.info("Added model to service", name=model_name, path=path)

    def _make_model_endpoint_fn(self, model, item_type):
        if isinstance(model, AsyncModel):

            async def _aendpoint(
                item: item_type = fastapi.Body(...),
                model=fastapi.Depends(lambda: self.lib.get(model.configuration_key)),
            ):  # noqa: B008
                return await model.predict(item)

            return _aendpoint

        def _endpoint(
            item: item_type = fastapi.Body(...),
            model=fastapi.Depends(lambda: self.lib.get(model.configuration_key)),
        ):  # noqa: B008
            return model.predict(item)

        return _endpoint

    def _make_batch_model_endpoint_fn(self, model, item_type):
        if isinstance(model, AsyncModel):

            async def _aendpoint(
                item: List[item_type] = fastapi.Body(...),
                model=fastapi.Depends(lambda: self.lib.get(model.configuration_key)),
            ):  # noqa: B008
                return await model.predict_batch(item)

            return _aendpoint

        def _endpoint(
            item: List[item_type] = fastapi.Body(...),
            model=fastapi.Depends(lambda: self.lib.get(model.configuration_key)),
        ):  # noqa: B008
            return model.predict_batch(item)

        return _endpoint


def create_modelkit_app(models=None, required_models=None):
    """
    Creates a modelkit FastAPI app with the specified models and required models.

    This is meant to be used in conjunction with gunicorn or uvicorn in order to
     start a server.

    Run with:
    ```
    export MODELKIT_REQUIRED_MODELS=... # optional
    export MODELKIT_DEFAULT_PACKAGE=... # mandatory
    gunicorn --workers 4 \
            --preload \
            --worker-class=uvicorn.workers.UvicornWorker \
            'modelkit.api.create_modelkit_app()'
    ```
    """
    if not (models or os.environ.get("MODELKIT_DEFAULT_PACKAGE")):
        raise ModelsNotFound(
            "Please add `your_package` as argument or set the "
            "`MODELKIT_DEFAULT_PACKAGE=your_package` env variable."
        )

    if os.environ.get("MODELKIT_REQUIRED_MODELS") and not required_models:
        required_models = os.environ.get("MODELKIT_REQUIRED_MODELS").split(":")
    app = fastapi.FastAPI()
    router = ModelkitAutoAPIRouter(required_models=required_models, models=models)
    app.include_router(router)
    return app
