import svgwrite
from gerber_format import GerberFormat
import layer

operations = layer.GerberLayer('example.gtl').read()

dwg = svgwrite.Drawing('test.svg', profile='tiny')
dwg.viewbox(width=50, height=50)

for op_type, point, state in operations:
    if op_type == GerberFormat.OPERATION_FLASH:
        dimension = state.aperture.dimension
        x = point[0] - (float(dimension[0]) / 2)
        y = point[1] - (float(dimension[1]) / 2)
        dwg.add(dwg.rect(insert=(x, y), size=dimension[:2]))
    elif op_type == GerberFormat.OPERATION_INTERP:
        pass

dwg.save()
