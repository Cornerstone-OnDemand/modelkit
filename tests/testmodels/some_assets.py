from modelkit.core.model import AbstractMixin, Asset, ConcreteMixin


class BaseAsset(AbstractMixin, Asset):
    def _load(self):
        assert self.asset_path


class DerivedAsset(ConcreteMixin, BaseAsset):
    CONFIGURATIONS = {"derived_asset": {"asset": "something.txt"}}
