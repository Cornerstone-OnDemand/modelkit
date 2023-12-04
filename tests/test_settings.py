import pydantic

from modelkit.core.settings import ModelkitSettings


def test_modelkit_settings_working(monkeypatch):
    class ServingSettings(ModelkitSettings):
        enable: bool = pydantic.Field(
            False,
            validation_alias=pydantic.AliasChoices(
                "enable",
                "SERVING_ENABLE",
            ),
        )

    assert ServingSettings().enable is False
    assert ServingSettings(enable=True).enable is True

    monkeypatch.setenv("SERVING_ENABLE", "True")
    assert ServingSettings().enable is True
    # without ModelkitSettings, the following would raise a ValidationError
    # because both `enable` and `SERVING_ENABLE` are set and passed to the
    # constructor.
    assert ServingSettings(enable=False).enable is False
