from modelkit.core.model import Model


class BaseModel(Model):
    def _load(self):
        assert self.asset_path


class DerivedModel(BaseModel):
    CONFIGURATIONS = {"derived_model": {"asset": "something.txt"}}

    def _predict(self, item):
        return item
