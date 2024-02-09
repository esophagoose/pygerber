import dataclasses
import logging
import re
from typing import List, Tuple

from pygerber.standards.nc_drill import NCDrillFormat


@dataclasses.dataclass(frozen=True)
class DrillHit:
    x: float
    y: float

    @classmethod
    def decode(cls, text):
        match = re.search(r"X([\+|\-|\d.]+)Y([\+|\-|\d.]+)", text)
        if match:
            x, y = match.groups()
            return cls(float(x), float(y))
        else:
            raise ValueError(f"Invalid XY format: {text}")

    def encode(self):
        x = int(self.x) if int(self.x) == self.x else self.x
        y = int(self.y) if int(self.y) == self.y else self.y
        return f"X{str(round(x, 6)).zfill(6)}Y{str(round(y, 6)).zfill(6)}"

    def get(self):
        return self.x, self.y


@dataclasses.dataclass(frozen=True)
class DrillOperation:
    tool: int
    point: DrillHit


@dataclasses.dataclass(frozen=True)
class RoutOperation:
    tool: int
    type: NCDrillFormat
    point: DrillHit


@dataclasses.dataclass(frozen=True)
class ToolOperation:
    down: bool


OPERATION_TYPES = [DrillOperation, RoutOperation, ToolOperation]


class DrillLayer:
    def __init__(self):
        self.tools = {}
        self.mode = NCDrillFormat.DRILL_MODE
        self.operations = []
        self.comments = ""
        self.units = None
        self._tool_index = None
        self._tool_to_index = {}
        self._index = 0

    def add_hole(self, x: float, y: float, diameter: float):
        if diameter not in self._tool_to_index:
            self._tool_to_index[diameter] = self._index
            self._index += 1
            self.tools[self._index] = diameter
        operation = DrillOperation(self._tool_to_index[diameter], DrillHit(x, y))
        self.operations.append(operation)

    def add_rout(
        self,
        points: List[Tuple[float, float]],
        diameter: float,
        interpolation=NCDrillFormat.LINEAR_ROUT,
    ):
        if diameter not in self._tool_to_index:
            self._tool_to_index[diameter] = self._index
            self._index += 1
            self.tools[self._index] = diameter
        for point in points:
            operation = RoutOperation(
                tool=self._tool_to_index[diameter],
                type=interpolation,
                point=DrillHit(*point),
            )
            self.operations.append(operation)

    def read(self, path) -> List[OPERATION_TYPES]:
        logging.info(f"Starting drill layer importer:")
        logging.info(f"\tFile: {path}")

        in_header = True
        with open(path, "r") as f:
            for index, line in enumerate(f.readlines()):
                line = line.strip()
                if not line:
                    continue
                logging.debug(f"Line: {index}, Processing: {line}")
                if line == NCDrillFormat.START_OF_HEADER.value:
                    in_header = True
                    continue
                if line == NCDrillFormat.END_OF_HEADER.value:
                    in_header = False
                    continue
                if in_header:
                    self._process_header(line)
                else:
                    self._process_content(line)
        return self.operations

    def _process_header(self, data):
        op_type, content = NCDrillFormat.lookup(data)

        if op_type == NCDrillFormat.COMMENT:
            self.comments += content[1:]
        elif op_type in [NCDrillFormat.SET_UNIT_MM, NCDrillFormat.SET_UNIT_INCH]:
            self.units = op_type.value
        elif op_type == NCDrillFormat.SELECT_TOOL:  # tool declaration
            index, diameter = re.search(r"T(\d+)C([\d.]+)", data).groups()
            self.tools[int(index)] = float(diameter)
        elif op_type == NCDrillFormat.FORMAT:
            return
        else:
            raise ValueError(f"Unknown command: {op_type}")

    def _process_content(self, data):
        op_type, content = NCDrillFormat.lookup(data)

        if op_type == NCDrillFormat.COMMENT:
            self.comments += content
        elif op_type in [NCDrillFormat.DRILL_MODE, NCDrillFormat.ROUT_MODE]:
            self.mode = op_type
            if content:
                operation = RoutOperation(
                    tool=self._tool_index,
                    type=op_type,
                    point=DrillHit.decode(content),
                )
                self.operations.append(operation)
        elif op_type == NCDrillFormat.SELECT_TOOL:
            index = int(content[1:])
            if index == 0:
                return
            self._tool_index = index
        elif op_type == NCDrillFormat.DRILL_HIT:
            assert self.mode == NCDrillFormat.DRILL_MODE, "Must be in drill mode to hit"
            operation = DrillOperation(
                tool=self._tool_index,
                point=DrillHit.decode(content),
            )
            self.operations.append(operation)
        elif op_type == NCDrillFormat.TOOL_DOWN:
            assert self.mode == NCDrillFormat.ROUT_MODE, f"Mode must be rout: {op_type}"
            self.operations.append(ToolOperation(True))
        elif op_type == NCDrillFormat.TOOL_UP:
            assert self.mode == NCDrillFormat.ROUT_MODE, f"Mode must be rout: {op_type}"
            self.operations.append(ToolOperation(False))
        elif op_type in [
            NCDrillFormat.LINEAR_ROUT,
            NCDrillFormat.CIRCULAR_CLOCKWISE_ROUT,
            NCDrillFormat.CIRCULAR_COUNTERCLOCKWISE_ROUT,
        ]:
            assert self.mode == NCDrillFormat.ROUT_MODE, "Must be in rout mode to rout"
            operation = RoutOperation(
                tool=self._tool_index,
                type=op_type,
                point=DrillHit.decode(content),
            )
            self.operations.append(operation)
        elif op_type in [NCDrillFormat.ABSOLUTE_UNITS, NCDrillFormat.END_OF_FILE]:
            return
        else:
            raise ValueError(f"Unknown command: {op_type}")

    def write(self, output_file):
        with open(output_file, "w") as f:
            # Write header
            f.write(f"{NCDrillFormat.START_OF_HEADER.value}\n")
            f.write(f"{self.units}\n")
            f.writelines([f"T{str(i).zfill(2)}C{d}\n" for i, d in self.tools.items()])
            f.write(f"{NCDrillFormat.END_OF_HEADER.value}\n")

            previous_op = None
            for index, op in enumerate(self.operations):
                if not isinstance(op, ToolOperation):
                    tool = f"T{str(op.tool).zfill(2)}\n"
                    if not previous_op or op.tool != previous_op.tool:
                        f.write(tool)
                if isinstance(op, RoutOperation):
                    f.write(f"{op.type.value}{op.point.encode()}\n")
                    previous_op = op
                elif isinstance(op, DrillOperation):
                    if not index or (self.operations[index - 1]) == RoutOperation:
                        f.write(f"{NCDrillFormat.DRILL_MODE.value}\n")
                    f.write(f"{op.point.encode()}\n")
                    previous_op = op
                elif isinstance(op, ToolOperation):
                    cmd = NCDrillFormat.TOOL_DOWN if op.down else NCDrillFormat.TOOL_UP
                    f.write(f"{cmd.value}\n")
                else:
                    raise ValueError(f"Invalid operation: {op}")
            f.write(f"{NCDrillFormat.END_OF_FILE.value}\n")
