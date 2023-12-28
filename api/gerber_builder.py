from typing import Tuple

import layers.aperture as ap_lib
import layers.gerber_layer as gl
import standard.gerber as gf


class GerberBuilder:
    def __init__(self, path, parameters={}) -> None:
        self.layer = gl.GerberLayer(path)
        self._set_standard_layer()
        for key, value in parameters:
            if not getattr(self.layer, key):
                raise ValueError(f"Unknown parameter: {key}")
            setattr(self.layer, key, value)

    def _set_standard_layer(self):
        self.layer.integer_digits = gf.Point(4, 4)
        self.layer.decimal_digits = gf.Point(6, 6)
        self.layer.scalars = (pow(10, -6), pow(10, -6))
        self.layer.quadrant_mode = gf.GerberFormat.QUADMODE_MULTI
        self.layer.units = gf.GerberFormat.UNITS
        self.layer.interpolation = gf.GerberFormat.INTERP_MODE_LINEAR
        self.layer.polarity = True

    def flash(self, aperture: ap_lib.APERTURES, position: Tuple[float, float]) -> None:
        if aperture not in self.layer.apertures:
            index = len(self.layer.apertures) + 1
            self.layer.apertures[index] = aperture
        self.layer.operations.append(self.layer.get_operation_state(aperture, position))
