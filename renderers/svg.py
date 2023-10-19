import math
import sys
from pathlib import Path

import svgwrite as svg

import layers.gerber_layer as gl
import layers.aperture as aperture_lib
import layers.drill_layer as drl
from standard.gerber import GerberFormat
from standard.nc_drill import NCDrillFormat


class SvgLayerRenderer:
    def __init__(self, back_color="white", fore_color="black"):
        self.background = back_color
        self.foreground = fore_color
        self.regions = []
        self.operations = []
        self.multilayer = []
        self.canvas = svg.container.Group()
        self._color = None
        self._drill_down = False
        self._layer = None
        self._previous_point = (0, 0)

    def add_layer(self, layer: gl.GerberLayer | drl.DrillLayer):
        self._layer = layer
        if isinstance(layer, gl.GerberLayer):
            self.add_gerber_layer(layer)
        elif isinstance(layer, drl.DrillLayer):
            self.add_drill_layer(layer)
        else:
            raise ValueError(f"Invalid layer type: {type(layer)}")

    def add_gerber_layer(self, layer: gl.GerberLayer):
        operations, regions = layer.read()
        for region in regions:
            obj = self._render_region(region)
            self.canvas.add(obj)

        for op_type, state in operations:
            self._color = self.foreground if state.polarity else self.background
            if op_type == GerberFormat.OPERATION_FLASH:
                obj = self._flash_aperture(state)
            elif op_type == GerberFormat.OPERATION_INTERP:
                obj = self._interpolate(state)
            elif op_type == GerberFormat.OPERATION_MOVE:
                continue  # moves are no-ops
            else:
                raise NotImplementedError(op_type, state)
            self.canvas.add(obj)
        return self

    def add_drill_layer(self, layer: drl.DrillLayer):
        for operation in layer.read():
            if isinstance(operation, drl.ToolOperation):
                self._drill_down = operation.down
                return
            point = operation.point.get()
            diameter = self._layer.tools[operation.tool]
            if isinstance(operation, drl.RoutOperation):
                if not self._drill_down:
                    self._previous_point = point
                    continue
                if operation.type == NCDrillFormat.LINEAR_ROUT:
                    obj = svg.shapes.Line(start=self._previous_point, end=point)
                    obj.stroke(self._color, width=diameter, linecap="round")
                else:
                    cw = int(operation.type == NCDrillFormat.CIRCULAR_CLOCKWISE_ROUT)
                    px, py = self._previous_point
                    obj = svg.path.Path("M{px},{py}").push_arc(
                        point, 0, r, large_arc=True, angle_dir="+", absolute=False
                    )
                    obj.stroke(self._color, width=diameter, linecap="round")
                self.canvas.add(obj)
            elif isinstance(operation, drl.DrillOperation):
                self.canvas.add(
                    svg.shapes.Circle(center=point, r=diameter / 2).fill(self._color)
                )
            else:
                raise ValueError(f"Invalid drill operation: {operation}")
        return self

    def save(self, output_folder):
        filepath = Path(output_folder) / Path(f"{self._layer.filename}.svg")
        drawing = svg.Drawing(filepath, profile="tiny")
        drawing.viewbox(width=50, height=50)
        # self.canvas.scale(1, -1)
        drawing.add(self.canvas)
        drawing.save()

    def _interpolate(self, state: gl.OperationState):
        height = state.aperture.dimension[0]
        cap = "square"
        if isinstance(state.aperture.shape, aperture_lib.ApertureCircle):
            cap = "round"

        if state.interpolation == GerberFormat.INTERP_MODE_LINEAR:
            line = svg.shapes.Line(start=state.previous_point, end=state.point)
            return line.stroke(self._color, width=height, linecap=cap)
        else:
            raise NotImplementedError("INTERPOLATE", state)

    def _flash_aperture(self, state: gl.OperationState):
        shape = state.aperture.shape
        if isinstance(shape, aperture_lib.ApertureCircle):
            return svg.shapes.Circle(center=state.point, r=shape.r).fill(self._color)
        elif isinstance(shape, aperture_lib.ApertureRectangle):
            size = (shape.width, shape.height)
            x = state.point[0] - (shape.width / 2)
            y = state.point[1] - (shape.height / 2)
            return svg.shapes.Rect(insert=(x, y), size=size).fill(self._color)
        elif isinstance(shape, aperture_lib.ApertureObround):
            size = (shape.width, shape.height)
            x = state.point[0] - (shape.width / 2)
            y = state.point[1] - (shape.height / 2)
            r = shape.height / 2
            return svg.shapes.Rect(insert=(x, y), size=size, rx=r, ry=r).fill(
                self._color
            )
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
        return svg.shapes.Polyline(points=points, fill=self._color)


if __name__ == "__main__":
    layer = gl.GerberLayer(sys.argv[1])
    SvgLayerRenderer(layer).save("./output_files/")
