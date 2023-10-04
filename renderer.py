import svgwrite as svg
from gerber_format import GerberFormat
import gerber_layer as gl
from pathlib import Path
import sys
import math


class RenderSvg:
    def __init__(self, layer, back_color="white", fore_color="black"):
        self.background = back_color
        self.foreground = fore_color
        self.operations, self.regions = layer.read()
        self.canvas = svg.container.Group()
        self._layer = layer

        for region in self.regions:
            obj = self._render_region(region)
            self.canvas.add(obj)

        for op_type, state in self.operations:
            color = self.foreground if state.polarity else self.background
            if op_type == GerberFormat.OPERATION_FLASH:
                obj = self._flash_aperture(state)
            elif op_type == GerberFormat.OPERATION_INTERP:
                obj = self._interpolate(state)
            elif op_type == GerberFormat.OPERATION_MOVE:
                continue  # moves are no-ops
            else:
                raise NotImplementedError(op_type, state)
            self.canvas.add(obj)

    def save(self, output_folder):
        filepath = Path(output_folder) / Path(f"{self._layer.filename}.svg")
        drawing = svg.Drawing(filepath, profile="tiny")
        drawing.viewbox(width=50, height=50)
        # self.canvas.scale(1, -1)
        drawing.add(self.canvas)
        drawing.save()

    def _interpolate(self, state):
        color = self.foreground if state.polarity else self.background
        height = state.aperture.dimension[0]
        cap = "round" if state.aperture.type == gl.ApertureTemplate.CIRCLE else "square"
        if state.interpolation == GerberFormat.INTERP_MODE_LINEAR:
            return svg.shapes.Line(start=state.previous_point, end=state.point).stroke(
                color, width=height, linecap=cap
            )
        else:
            raise NotImplementedError("INTERPOLATE", state)

    def _flash_aperture(self, state):
        color = self.foreground if state.polarity else self.background
        if state.aperture.type == gl.ApertureTemplate.CIRCLE:
            for diameter in state.aperture.dimension:
                radius = diameter / 2
                return svg.shapes.Circle(center=state.point, r=radius).fill(color)
        elif state.aperture.type in [
            gl.ApertureTemplate.RECT,
            gl.ApertureTemplate.OBROUND,
        ]:
            w, h = state.aperture.dimension
            x = state.point[0] - (w / 2)
            y = state.point[1] - (h / 2)
            r = h / 2 if state.aperture.type == gl.ApertureTemplate.OBROUND else 0
            return svg.shapes.Rect(insert=(x, y), size=(w, h)).fill(color)
        else:
            raise NotImplementedError("FLASH", state)

    def _render_region(self, region):
        points = []
        for op_type, state in region:
            if op_type == GerberFormat.OPERATION_MOVE:
                pass
            elif op_type != GerberFormat.OPERATION_INTERP:
                raise ValueError(f"Invalid region operation: {op_type}")
            points.append(state.point)
        color = self.foreground if state.polarity else self.background
        return svg.shapes.Polyline(points=points, fill=color)


if __name__ == "__main__":
    layer = gl.GerberLayer(sys.argv[1])
    RenderSvg(layer).save("./output_files/")
