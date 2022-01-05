from modelkit.core.model import AbstractMixin, ConcreteMixin, Model


class BaseModel(AbstractMixin, Model):
    def _load(self):
        assert self.asset_path


class DerivedModel(ConcreteMixin, BaseModel):
    CONFIGURATIONS = {"derived_model": {"asset": "something.txt"}}

    def _predict(self, item):
        return item
