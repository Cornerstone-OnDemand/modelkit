from modelkit.core.model import Model


class BadModel(Model[int, int]):
    def _predict_one(self, item):
        return item


m = BadModel()
y = m("some string")
