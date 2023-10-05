import logging
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
        self._selected_tool = None
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
        elif op_type == NCDrillFormat.TOOL_COMMAND:
            index = int(content[1:])
            if index == 0:
                return
            self._selected_tool = self.tools[index]
        elif op_type == NCDrillFormat.DRILL_HIT:
            assert self.mode == NCDrillFormat.DRILL_MODE, "Must be in drill mode to hit"
            point = parse_xy(content)
            self.operations.append((self.mode, self._selected_tool, point))
        elif op_type == NCDrillFormat.TOOL_DOWN:
            self._routing = True
        elif op_type == NCDrillFormat.TOOL_UP:
            self.operations.append((self.mode, self._selected_tool, self._rout))
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
