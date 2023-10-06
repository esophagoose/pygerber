import layers.drill_layer as drl


class Drilling:
    def __init__(self):
        self.layer = drl.DrillLayer()
        self._diameter_to_index = {}
        self._index = 0

    def add(self, x: float, y: float, d: float):
        if d not in self._diameter_to_index:
            self._diameter_to_index[d] = self._index
            self._index += 1
            self.layer.tools[self._index] = d
        operation = drl.DrillOperation(
            tool=self._diameter_to_index[d],
            point=drl.DrillHit(x, y)
        )
        self.layer.operations.append(operation)
