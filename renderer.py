import svgwrite as svg
from gerber_format import GerberFormat
import gerber_layer as gl
from pathlib import Path
import sys


class RenderSvg:
    def __init__(self, layer):
        self.background = "white"
        self.foreground = "red"
        self.operations, self.regions = layer.read()
        self.canvas = svg.container.Group()
        self._layer = layer

        for region in self.regions:
            obj = self._render_region(region)
            self.canvas.add(obj)

        for op_type, state in self.operations:
            color = self.foreground if state.polarity else self.background
            if op_type == GerberFormat.OPERATION_FLASH:
                if state.aperture.type == gl.ApertureTemplate.CIRCLE:
                    for diameter in state.aperture.dimension:
                        radius = float(diameter) / 2
                        obj = svg.shapes.Circle(center=state.point, r=radius)
                        obj.fill(color)
                elif state.aperture.type == gl.ApertureTemplate.RECT:
                    w, h = state.aperture.dimension
                    x = state.point[0] - (float(w) / 2)
                    y = state.point[1] - (float(h) / 2)
                    obj = svg.shapes.Rect(insert=(x, y), size=(w, h))
                    obj.fill(color)
                else:
                    raise NotImplementedError(state)
            elif op_type == GerberFormat.OPERATION_INTERP:
                if state.interpolation == GerberFormat.INTERP_MODE_LINEAR:
                    obj = svg.shapes.Line(
                        start=state.previous_point, end=state.point
                    ).stroke(color, width=state.aperture.dimension[0])
                else:
                    raise NotImplementedError(state)
            elif op_type == GerberFormat.OPERATION_MOVE:
                continue  # moves are no-ops
            else:
                raise NotImplementedError(state)
            self.canvas.add(obj)

    def save(self, output_folder):
        filepath = Path(output_folder) / Path(f"{self._layer.filename}.svg")
        drawing = svg.Drawing(filepath, profile="tiny")
        drawing.viewbox(width=50, height=50)
        drawing.add(self.canvas)
        drawing.save()

    def _render_region(self, region):
        points = []
        for op_type, state in region:
            if op_type == GerberFormat.OPERATION_MOVE:
                pass
            elif op_type != GerberFormat.OPERATION_INTERP:
                raise ValueError(f"Invalid region operation: {op_type}")
            points.append(state.point)
        color = self.foreground if state.polarity else self.background
        return svg.shapes.Polyline(
            points=points, fill=color, stroke=color, stroke_width=0.1
        )


if __name__ == "__main__":
    layer = gl.GerberLayer(sys.argv[1])
    RenderSvg(layer).save("./output_files/")
