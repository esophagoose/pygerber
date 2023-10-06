import logging
import copy
import os
import re

from standard.nc_drill import NCDrillFormat


def parse_xy(text):
    match = re.search(r"X([\+|\-|\d.]+)Y([\+|\-|\d.]+)", text)
    if match:
        x, y = match.groups()
        return float(x), float(y)
    else:
        raise ValueError(f"Invalid XY format: {text}")


def point_to_drill_hit(pt):
    x = int(pt[0]) if int(pt[0]) == pt[0] else pt[0]
    y = int(pt[1]) if int(pt[1]) == pt[1] else pt[1]
    return f"X{str(round(x, 6)).zfill(6)}Y{str(round(y, 6)).zfill(6)}"


class DrillLayer:
    def __init__(self, filepath):
        logging.info(f"Starting drill layer importer:")
        logging.info(f"\tFile: {filepath}")

        self.filename = os.path.basename(filepath)
        self.path = filepath
        self.tools = {}
        self.mode = NCDrillFormat.DRILL_MODE
        self.operations = []
        self.comments = ""
        self._tool_index = None
        self._rout = []
        self._routing = False

    def read(self):
        in_header = True
        with open(self.path, "r") as f:
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
        elif op_type == NCDrillFormat.TOOL_COMMAND:  # tool declaration
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
                point = parse_xy(content)
                self.operations.append((self.mode, self._tool_index, point))
        elif op_type == NCDrillFormat.TOOL_COMMAND:
            index = int(content[1:])
            if index == 0:
                return
            self._tool_index = index
        elif op_type == NCDrillFormat.DRILL_HIT:
            assert self.mode == NCDrillFormat.DRILL_MODE, "Must be in drill mode to hit"
            point = parse_xy(content)
            self.operations.append((self.mode, self._tool_index, point))
        elif op_type == NCDrillFormat.TOOL_DOWN:
            self._routing = True
        elif op_type == NCDrillFormat.TOOL_UP:
            self.operations.append(
                (self.mode, self._tool_index, copy.deepcopy(self._rout))
            )
            self._rout.clear()
            self._routing = False
        elif op_type == NCDrillFormat.LINEAR_ROUT:
            assert self._routing, f"Invalid {op_type} while tool is up"
            self._rout.append((op_type, parse_xy(content)))
        elif op_type == NCDrillFormat.CIRCULAR_CLOCKWISE_ROUT:
            assert self._routing, f"Invalid {op_type} while tool is up"
            self._rout.append((op_type, parse_xy(content)))
        elif op_type == NCDrillFormat.CIRCULAR_COUNTERCLOCKWISE_ROUT:
            assert self._routing, f"Invalid {op_type} while tool is up"
            self._rout.append((op_type, parse_xy(content)))
        elif op_type in [NCDrillFormat.ABSOLUTE_UNITS, NCDrillFormat.END_OF_FILE]:
            return
        else:
            raise ValueError(f"Unknown command: {op_type}")

    def _write_drill(self, operation, f, skip_mode=False, skip_tool=False):
        mode, tool_index, point = operation
        tool = f"T{str(tool_index).zfill(2)}\n"
        if not skip_mode:
            f.write(mode.value + "\n")
        if not skip_tool:
            f.write(tool)
        f.write(point_to_drill_hit(point) + "\n")

    def _write_rout(self, operation, f, skip_mode=False, skip_tool=False):
        mode, tool_index, steps = operation
        tool = f"T{str(tool_index).zfill(2)}\n"
        if isinstance(steps[0], (int, float)) and len(steps) == 2:
            f.write(f"{mode.value}{point_to_drill_hit(steps)}\n")
            return
        route = [f"{op.value}{point_to_drill_hit(xy)}\n" for op, xy in steps]
        if not skip_mode:
            f.write(mode.value + "\n")
        if not skip_tool:
            f.write(tool)
        f.write(NCDrillFormat.TOOL_DOWN.value + "\n")
        f.writelines(route)
        f.write(NCDrillFormat.TOOL_UP.value + "\n")

    def write(self, output_file):
        def _newline(text):
            return f"{text}\n"

        with open(output_file, "w") as f:
            # Write header
            f.write(_newline(NCDrillFormat.START_OF_HEADER.value))
            f.write(_newline(self.units))
            f.writelines([f"T{i}C{d}\n" for i, d in self.tools.items()])
            f.write(_newline(NCDrillFormat.END_OF_HEADER.value))

            prev_tool = None
            prev_mode = None
            for op in self.operations:
                mode, tool, _ = op
                same_mode = prev_mode == mode
                same_tool = prev_tool == tool
                if mode == NCDrillFormat.ROUT_MODE:
                    self._write_rout(op, f, same_mode, same_tool)
                else:
                    self._write_drill(op, f, same_mode, same_tool)
                prev_mode = mode
                prev_tool = tool
            f.writelines([NCDrillFormat.END_OF_FILE.value])
