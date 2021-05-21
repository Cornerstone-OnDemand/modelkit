import os

import pytest

from modelkit import testing
from modelkit.core.library import (
    ConfigurationNotFoundException,
    ModelLibrary,
    download_assets,
    load_model,
)
from modelkit.core.model import Asset, Model, NoModelDependenciesInInitError
from modelkit.core.model_configuration import (
    ModelConfiguration,
    _configurations_from_objects,
    configure,
    list_assets,
)
from modelkit.core.settings import ServiceSettings
from modelkit.utils.tensorflow import write_config
from tests import TEST_DIR


def test_override_asset():
    class TestModel(Model):
        def _deserialize_asset(self):
            pass

        async def _predict_one(self, item, **kwargs):
            return self.asset_path

    class TestDepModel(Model):
        async def _predict_one(self, item, **kwargs):
            return "dep" + self.asset_path

    config = {
        "some_asset": ModelConfiguration(
            model_type=TestModel,
            asset="asset/that/does/not/exist",
            model_dependencies={"dep_model"},
        ),
        "dep_model": ModelConfiguration(model_type=TestDepModel),
    }
    # The asset does not exist
    with pytest.raises(Exception):
        prediction_service = ModelLibrary(
            required_models=["some_asset"], configuration=config
        )

    # It does when overriden
    prediction_service = ModelLibrary(
        required_models={"some_asset": {"asset_path": "/the/path"}},
        configuration=config,
    )
    model = prediction_service.get_model("some_asset")
    assert "/the/path" == model.predict({})

    # Dependent models are loaded properly
    model = prediction_service.get_model("dep_model")
    assert "dep" == model.predict({})

    # Finally, it is possible to also specify
    # an asset for the dependent model
    config["dep_model"] = ModelConfiguration(
        model_type=TestDepModel, asset="cat/someasset"
    )
    prediction_service = ModelLibrary(
        required_models={
            "some_asset": {"asset_path": "/the/path"},
            "dep_model": {"asset_path": "/the/dep/path"},
        },
        configuration=config,
    )
    # Dependent models are loaded properly
    model = prediction_service.get_model("dep_model")
    assert "dep/the/dep/path" == model.predict({})


def test_prediction_service_inexistent_model():
    with pytest.raises(ConfigurationNotFoundException):
        ModelLibrary(required_models=["model_that_does_not_exist"])

    configuration = {
        "existent_model": ModelConfiguration(
            model_type=Model, model_dependencies={"inexistent_model"}
        )
    }
    with pytest.raises(ConfigurationNotFoundException):
        ModelLibrary(required_models=["existent_model"], configuration=configuration)

    p = ModelLibrary(
        required_models=["model_that_does_not_exist"], settings={"lazy_loading": True}
    )
    with pytest.raises(ConfigurationNotFoundException):
        p.get_model("model_that_does_not_exist")
    with pytest.raises(ConfigurationNotFoundException):
        p.get_model("other_model_that_does_not_exist")


def test__configurations_from_objects():
    class SomeModel(Model):
        CONFIGURATIONS = {"yolo": {}, "les simpsons": {}}

    class SomeModel2(Asset):
        CONFIGURATIONS = {"yolo2": {}, "les simpsons2": {}}

    class ModelNoConf(Asset):
        pass

    configurations = _configurations_from_objects(SomeModel)
    assert "yolo" in configurations
    assert "les simpsons" in configurations

    configurations = _configurations_from_objects(ModelNoConf)
    assert {} == configurations

    configurations = _configurations_from_objects([SomeModel, SomeModel2, ModelNoConf])
    assert "yolo" in configurations
    assert "yolo2" in configurations
    assert "les simpsons" in configurations
    assert "les simpsons2" in configurations

    class Something:
        pass

    with pytest.raises(ValueError):
        _configurations_from_objects(Something)


def test_configure_override():
    class SomeModel(Model):
        CONFIGURATIONS = {"yolo": {"asset": "ok/boomer"}, "les simpsons": {}}

    class SomeOtherModel(Model):
        pass

    configurations = configure(models=SomeModel)
    assert configurations["yolo"].model_type == SomeModel
    assert configurations["yolo"].asset == "ok/boomer"
    assert configurations["les simpsons"].model_type == SomeModel
    assert configurations["les simpsons"].asset is None

    configurations = configure(
        models=SomeModel,
        configuration={"somethingelse": ModelConfiguration(model_type=SomeOtherModel)},
    )
    assert configurations["yolo"].model_type == SomeModel
    assert configurations["yolo"].asset == "ok/boomer"
    assert configurations["les simpsons"].model_type == SomeModel
    assert configurations["les simpsons"].asset is None
    assert configurations["somethingelse"].model_type == SomeOtherModel
    assert configurations["somethingelse"].asset is None

    configurations = configure(
        models=SomeModel,
        configuration={"yolo": ModelConfiguration(model_type=SomeOtherModel)},
    )
    assert configurations["yolo"].model_type == SomeOtherModel
    assert configurations["yolo"].asset is None

    configurations = configure(
        models=SomeModel,
        configuration={"yolo": {"asset": "something/else"}},
    )
    assert configurations["yolo"].model_type == SomeModel
    assert configurations["yolo"].asset == "something/else"

    configurations = configure(
        models=SomeModel,
        configuration={"yolo2": {"model_type": SomeOtherModel}},
    )
    assert configurations["yolo"].model_type == SomeModel
    assert configurations["yolo"].asset == "ok/boomer"
    assert configurations["yolo2"].model_type == SomeOtherModel
    assert configurations["yolo2"].asset is None


def test_modellibrary_required_models():
    class SomeModel(Model):
        CONFIGURATIONS = {"yolo": {}, "les simpsons": {}}

    p = ModelLibrary(models=SomeModel)
    m = p.get_model("yolo")
    assert m
    assert m.configuration_key == "yolo"
    assert m.model_classname == "SomeModel"
    assert m.model_settings == {}
    assert m.asset_path == ""
    assert m.batch_size == 64


def test_modellibrary_no_models(monkeypatch):
    monkeypatch.setenv("modelkit_MODELS", "")
    p = ModelLibrary(models=None)
    assert p.configuration == {}
    assert p.required_models == {}


def test_lazy_loading_dependencies():
    class Model0(Asset):
        CONFIGURATIONS = {"model0": {}}

        def _deserialize_asset(self):
            self.some_attribute = "ok"

    class Model1(Model):
        CONFIGURATIONS = {"model1": {"model_dependencies": {"model0"}}}

        def _deserialize_asset(self):
            self.some_attribute = self.model_dependencies["model0"].some_attribute

        async def _predict_one(self, item):
            return self.some_attribute

    p = ModelLibrary(models=[Model1, Model0], settings={"lazy_loading": True})
    m = p.get_model("model1")
    assert m.predict({}) == "ok"
    assert m.model_dependencies["model0"].some_attribute == "ok"
    assert m.some_attribute == "ok"


def test_dependencies_not_in_init():
    class Model0(Asset):
        CONFIGURATIONS = {"model0": {}}

        def _deserialize_asset(self):
            self.some_attribute = "ok"

    class Model1(Model):
        CONFIGURATIONS = {"model1": {"model_dependencies": {"model0"}}}

        def __init__(self, *args, **kwargs):
            self.some_attribute = self.model_dependencies["model0"].some_attribute
            super().__init__(self, *args, **kwargs)

    with pytest.raises(NoModelDependenciesInInitError):
        ModelLibrary(models=[Model1, Model0])

    class Model11(Model):
        CONFIGURATIONS = {"model11": {"model_dependencies": {"model0"}}}

        def __init__(self, *args, **kwargs):
            super().__init__(self, *args, **kwargs)
            self.some_attribute = self.model_dependencies["model0"].some_attribute

    with pytest.raises(NoModelDependenciesInInitError):
        ModelLibrary(models=[Model11, Model0])


def test_list_assets():
    class SomeModel(Asset):
        CONFIGURATIONS = {"model0": {"asset": "some/asset"}}

    class SomeOtherModel(Asset):
        CONFIGURATIONS = {"model1": {"asset": "some/asset"}}

    assert {"some/asset"} == list_assets(SomeModel)
    assert {"some/asset"} == list_assets([SomeModel, SomeOtherModel])
    assert {"some/asset", "some/otherasset"} == list_assets(
        [SomeModel, SomeOtherModel],
        configuration={"model1": {"asset": "some/otherasset"}},
    )
    assert {"some/asset"} == list_assets(
        [SomeModel, SomeOtherModel],
        required_models=["model0"],
        configuration={"model1": {"asset": "some/otherasset"}},
    )


@pytest.fixture
def assetsmanager_settings(working_dir):
    yield {
        "remote_store": {
            "driver": {
                "storage_provider": "local",
                "bucket": os.path.join(TEST_DIR, "testdata", "test-bucket"),
            },
            "assetsmanager_prefix": "assets-prefix",
        },
        "assets_dir": working_dir,
    }


def test_download_assets_version(assetsmanager_settings):
    class SomeModel(Asset):
        CONFIGURATIONS = {"model0": {"asset": "category/asset:0.0"}}

    model_assets, assets_info = download_assets(
        assetsmanager_settings=assetsmanager_settings,
        models=[SomeModel],
    )
    assert model_assets["model0"] == {"category/asset:0.0"}
    assert assets_info["category/asset:0.0"]["version"] == "0.0"

    class SomeModel(Asset):
        CONFIGURATIONS = {"model0": {"asset": "category/asset"}}

    model_assets, assets_info = download_assets(
        assetsmanager_settings=assetsmanager_settings,
        models=[SomeModel],
    )
    assert model_assets["model0"] == {"category/asset"}
    assert assets_info["category/asset"]["version"] == "1.0"

    class SomeModel(Asset):
        CONFIGURATIONS = {"model0": {"asset": "category/asset:0"}}

    model_assets, assets_info = download_assets(
        assetsmanager_settings=assetsmanager_settings,
        models=[SomeModel],
    )
    assert model_assets["model0"] == {"category/asset:0"}
    assert assets_info["category/asset:0"]["version"] == "0.1"


def test_download_assets_dependencies(assetsmanager_settings):
    class SomeModel(Asset):
        CONFIGURATIONS = {"model0": {"asset": "category/asset"}}

    class SomeOtherModel(Asset):
        CONFIGURATIONS = {
            "model1": {"asset": "category/asset:0", "model_dependencies": {"model0"}}
        }

    model_assets, assets_info = download_assets(
        assetsmanager_settings=assetsmanager_settings,
        models=[SomeModel, SomeOtherModel],
    )

    assert model_assets["model0"] == {"category/asset"}
    assert model_assets["model1"] == {"category/asset:0", "category/asset"}
    assert assets_info["category/asset"]["version"] == "1.0"
    assert assets_info["category/asset:0"]["version"] == "0.1"


def test_write_tf_serving_config(base_dir, assetsmanager_settings):
    write_config(os.path.join(base_dir, "test.config"), {"model0": "/some/path"})
    ref = testing.ReferenceText(os.path.join(TEST_DIR, "testdata"))
    with open(os.path.join(base_dir, "test.config")) as f:
        ref.assert_equal("test.config", f.read())


def test_load_model():
    class SomeModel(Model):
        CONFIGURATIONS = {"model": {}}

        async def _predict_one(self, item):
            return item

    m = load_model("model", models=SomeModel)
    assert m.predict({"ok": "boomer"}) == {"ok": "boomer"}


def test_required_models():
    class SomeModel(Model):
        CONFIGURATIONS = {"model": {}}

    class SomeOtherModel(Model):
        CONFIGURATIONS = {"other_model": {}}

    svc = ModelLibrary(required_models=[], models=[SomeModel, SomeOtherModel])
    assert len(svc.models) == 0
    assert svc.required_models == {}

    svc = ModelLibrary(models=[SomeModel, SomeOtherModel])
    assert len(svc.models) == 2
    assert svc.required_models == {"model": {}, "other_model": {}}


def test_lazy_loading_setting(monkeypatch):
    monkeypatch.delenv("LAZY_LOADING", raising=False)
    settings = ServiceSettings()
    assert not settings.lazy_loading
    monkeypatch.setenv("LAZY_LOADING", "True")
    settings = ServiceSettings()
    assert settings.lazy_loading


def test_environment_asset_load(monkeypatch, assetsmanager_settings):
    class TestModel(Model):
        def _deserialize_asset(self):
            assert self.asset_path == "path/to/asset"
            self.data = {"some key": "some data"}

        async def _predict_one(self, item, **kwargs):
            return self.data

    monkeypatch.setenv("modelkit_TESTS_TEST_ASSET_FILE", "path/to/asset")

    prediction_service = ModelLibrary(
        required_models=["some_asset"],
        configuration={
            "some_asset": ModelConfiguration(
                model_type=TestModel, asset="tests/test_asset"
            )
        },
        assetsmanager_settings=assetsmanager_settings,
    )
    model = prediction_service.get_model("some_asset")

    predicted = model.predict({})
    assert predicted == {"some key": "some data"}


def test_rename_dependencies():
    class SomeModel(Model):
        CONFIGURATIONS = {"ok": {}}

        async def _predict_one(self, item):
            return self.configuration_key

    class SomeModel2(Model):
        CONFIGURATIONS = {"boomer": {}}

        async def _predict_one(self, item):
            return self.configuration_key

    class FinalModel(Model):
        CONFIGURATIONS = {
            "model_no_rename": {
                "model_dependencies": {"ok"},
            },
            "model_rename": {
                "model_dependencies": {"ok": "boomer"},
            },
        }

        async def _predict_one(self, item):
            return self.model_dependencies["ok"].predict(item)

    svc = ModelLibrary(models=[SomeModel, SomeModel2, FinalModel])
    assert svc.get_model("model_no_rename").predict({}) == "ok"
    assert svc.get_model("model_rename").predict({}) == "boomer"


def test_override_prefix(assetsmanager_settings):
    class TestModel(Model):
        async def _predict_one(self, item, **kwargs):
            return self.asset_path

    prediction_service = ModelLibrary(
        required_models=["my_model", "my_override_model"],
        configuration={
            "my_model": ModelConfiguration(
                model_type=TestModel, asset="category/asset"
            ),
            "my_override_model": ModelConfiguration(
                model_type=TestModel, asset="category/override-asset"
            ),
        },
        assetsmanager_settings=assetsmanager_settings,
    )

    prediction = prediction_service.get_model("my_model").predict({})
    assert prediction.endswith(os.path.join("category", "asset", "1.0"))

    prediction = prediction_service.get_model("my_override_model").predict({})
    assert prediction.endswith(os.path.join("category", "override-asset", "0.0"))

    prediction_service = ModelLibrary(
        required_models=["my_model", "my_override_model"],
        configuration={
            "my_model": ModelConfiguration(
                model_type=TestModel, asset="category/asset"
            ),
            "my_override_model": ModelConfiguration(
                model_type=TestModel, asset="category/override-asset"
            ),
        },
        settings={"override_assetsmanager_prefix": "override-assets-prefix"},
        assetsmanager_settings=assetsmanager_settings,
    )

    prediction = prediction_service.get_model("my_model").predict({})
    assert prediction.endswith(os.path.join("category", "asset", "1.0"))

    prediction = prediction_service.get_model("my_override_model").predict({})
    assert prediction.endswith(os.path.join("category", "override-asset", "1.0"))
