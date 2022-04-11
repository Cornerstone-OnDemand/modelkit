from modelkit.core.model import Asset


class BaseAsset(Asset):
    def _load(self):
        assert self.asset_path


class DerivedAsset(BaseAsset):
    CONFIGURATIONS = {"derived_asset": {"asset": "something.txt"}}
