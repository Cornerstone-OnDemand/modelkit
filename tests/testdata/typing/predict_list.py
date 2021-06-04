from typing import List

from modelkit.core.model import Model


class M(Model[List[int], int]):
    def _predict(self, item):
        return sum(item)
