from modelkit.core.model import Model


class BadModel(Model[int, int]):
    def _predict(self, item):
        return item


m = BadModel()
y = m("some string")
